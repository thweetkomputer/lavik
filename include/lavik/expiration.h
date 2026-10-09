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
#include <limits>
#include <string_view>

#include "absl/status/statusor.h"
#include "absl/strings/str_cat.h"
#include "lavik/redis_parse.h"

namespace lavik {

enum class PastExpirationPolicy : std::uint8_t {
  kExpireImmediately,
  kRejectNonPositive,
};

inline std::uint64_t RedisUnixTimeMillis() noexcept {
  const auto value = std::chrono::duration_cast<std::chrono::milliseconds>(
                         std::chrono::system_clock::now().time_since_epoch())
                         .count();
  return value > 0 ? static_cast<std::uint64_t>(value) : 0;
}

inline absl::StatusOr<std::uint64_t> ParseRedisExpirationDeadline(
    std::string_view text, bool seconds, bool absolute,
    std::string_view command, PastExpirationPolicy past_policy) {
  std::int64_t value = 0;
  if (!ParseRedisInt64(text, &value)) {
    return absl::InvalidArgumentError(
        "value is not an integer or out of range");
  }
  auto invalid = [&] {
    return absl::InvalidArgumentError(
        absl::StrCat("invalid expire time in '", command, "' command"));
  };
  if (past_policy == PastExpirationPolicy::kRejectNonPositive && value <= 0) {
    return invalid();
  }
  if (seconds && (value > std::numeric_limits<std::int64_t>::max() / 1000 ||
                  value < std::numeric_limits<std::int64_t>::min() / 1000)) {
    return invalid();
  }
  if (seconds) value *= 1000;

  const std::int64_t now = static_cast<std::int64_t>(RedisUnixTimeMillis());
  if (!absolute) {
    if (value > std::numeric_limits<std::int64_t>::max() - now) {
      return invalid();
    }
    value += now;
  }
  if (past_policy == PastExpirationPolicy::kExpireImmediately && value <= now) {
    // Storage uses zero for persistence, so an elapsed deadline needs a
    // positive sentinel that the write path immediately converts to a tomb.
    return std::uint64_t{1};
  }
  if (value <= 0) return invalid();
  return static_cast<std::uint64_t>(value);
}

}  // namespace lavik
