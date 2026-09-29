/*
 * Copyright (C) 2026 EloqData Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     https://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#pragma once

#include <array>
#include <chrono>
#include <cstdlib>

#include "spdlog/spdlog.h"

namespace lavik::storage::write_stage_diagnostic {
enum Phase {
  kCommand,
  kInitialLock,
  kRead,
  kPlan,
  kCommit,
  kDependency,
  kPressure,
  kAuxiliary,
  kRoot,
  kCount
};
inline constexpr std::array<const char*, kCount> names{
    "command",    "initial_lock", "read_decode", "plan", "commit",
    "dependency", "pressure",     "auxiliary",   "root"};
struct Stats {
  std::uint64_t count = 0, nanos = 0, maximum = 0;
};
inline thread_local std::array<Stats, kCount> stats;
inline std::uint64_t Now() {
  return std::chrono::duration_cast<std::chrono::nanoseconds>(
             std::chrono::steady_clock::now().time_since_epoch())
      .count();
}
class Stage {
 public:
  explicit Stage(Phase phase, bool eligible = true) : phase_(phase) {
    static const bool enabled = std::getenv("LAVIK_WRITE_STAGES") != nullptr;
    if (enabled && eligible) start_ = Now();
  }
  ~Stage() { Finish(); }
  void Finish() {
    if (!start_) return;
    const auto elapsed = Now() - start_;
    start_ = 0;
    auto& value = stats[phase_];
    ++value.count;
    value.nanos += elapsed;
    value.maximum = std::max(value.maximum, elapsed);
    if (value.count % 4096 == 0)
      spdlog::info("write-stage worker={} phase={} n={} avg_us={} max_us={}",
                   bycorf::ThisWorker().id_, names[phase_], value.count,
                   double(value.nanos) / value.count / 1000,
                   double(value.maximum) / 1000);
  }

 private:
  Phase phase_;
  std::uint64_t start_ = 0;
};
}  // namespace lavik::storage::write_stage_diagnostic
