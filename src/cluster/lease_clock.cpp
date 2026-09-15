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

#include "keylane/cluster/lease_clock.h"

#include <time.h>

#include <chrono>
#include <exception>

#if !defined(__linux__) || !defined(CLOCK_BOOTTIME)
#error "finite cluster leases require Linux CLOCK_BOOTTIME"
#endif

namespace keylane::cluster {

LeaseTime LeaseClockNow() noexcept {
  timespec now{};
  if (::clock_gettime(CLOCK_BOOTTIME, &now) != 0) {
    // Falling back after deadlines have been created would mix clock epochs
    // and could revive expired authority. CLOCK_BOOTTIME is mandatory on the
    // supported Linux runtime, so an unavailable clock is a fail-stop fault.
    std::terminate();
  }
  const auto seconds = std::chrono::seconds(now.tv_sec);
  const auto nanoseconds = std::chrono::nanoseconds(now.tv_nsec);
  return LeaseTime(
      std::chrono::duration_cast<LeaseDuration>(seconds + nanoseconds));
}

}  // namespace keylane::cluster
