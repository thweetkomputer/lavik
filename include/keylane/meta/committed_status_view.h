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

// Compact atomic projection used only by cluster status. It deliberately
// excludes audit records, policy bodies, operation payload/evidence, and the
// complete eight-store aggregate so an operator read has bounded cost tied to
// current identity/topology rather than retained history.

#include <cstdint>
#include <string>
#include <vector>

#include "keylane/meta/grant_store.h"
#include "keylane/meta/identity_store.h"
#include "keylane/meta/topology_store.h"

namespace keylane::meta {

struct MetaCommittedStatusGroup {
  MetaTopologyGroupView topology_;
  MetaGroupGrantState grant_;
  bool manifest_present_ = false;
  bool policy_active_ = false;
};

struct MetaCommittedStatusSlotRange {
  std::uint32_t first_ = 0;
  std::uint32_t last_ = 0;
  std::string group_id_;
};

struct MetaCommittedStatusView {
  std::uint64_t applied_index_ = 0;
  std::uint64_t topology_epoch_ = 0;
  bool active_cluster_create_operation_ = false;
  // The compact creation projection retains only diagnostic routing facts,
  // never the complete operation intent or destructive workflow evidence.
  std::string active_cluster_create_phase_;
  std::vector<std::string> active_cluster_create_data_nodes_;
  std::vector<MetaMemberRecord> meta_members_;
  std::vector<MetaNodeRecord> data_nodes_;
  std::vector<MetaCommittedStatusGroup> groups_;
  std::vector<MetaCommittedStatusSlotRange> slot_ranges_;
};

}  // namespace keylane::meta
