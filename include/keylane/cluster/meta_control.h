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

// Data-side adapter from authenticated control-protocol values into the
// immutable serving domain. Decoding a frame is intentionally insufficient:
// this boundary validates node/group relationships and builds the complete
// snapshot before NodeControlInstaller can publish anything.

#include <cstddef>
#include <string_view>

#include "absl/status/statusor.h"
#include "keylane/cluster/control_protocol.h"
#include "keylane/cluster/node_control.h"

namespace keylane::cluster {

absl::StatusOr<PreparedFullState> PrepareMetaFullState(
    const control::FullDesiredState& desired, std::string_view local_node_id,
    std::size_t request_worker_count);

// Validates selected node state and derives routing plus local execution state.
absl::StatusOr<PreparedFullState> PrepareNodeControlState(
    const control::NodeControlState& state, std::string_view local_node_id,
    std::size_t request_worker_count);

}  // namespace keylane::cluster
