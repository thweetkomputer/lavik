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

#include <chrono>
#include <cstdint>

namespace lavik::cluster {

// Lease deadlines need elapsed time to advance while the host is suspended.
// std::chrono::steady_clock maps to CLOCK_MONOTONIC on Linux and therefore
// pauses across suspend. Keep the existing steady-clock representation so
// callers can inject deterministic time points in tests, but obtain every
// production lease timestamp through LeaseClockNow(), which uses
// CLOCK_BOOTTIME. Lavik is Linux-only; there is intentionally no fallback
// to a clock that could let an old authority survive suspend/resume.
using LeaseTime = std::chrono::steady_clock::time_point;
using LeaseDuration = std::chrono::steady_clock::duration;

LeaseTime LeaseClockNow() noexcept;

inline std::int64_t LeaseClockMillis() noexcept {
  return std::chrono::duration_cast<std::chrono::milliseconds>(
             LeaseClockNow().time_since_epoch())
      .count();
}

}  // namespace lavik::cluster
