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

#include <cstddef>
#include <cstdint>

namespace keylane::storage {

// Copied population identity for collection read/modify/write that releases
// worker store state while retaining exclusive key intent and database
// admission. Compact writes retain a RecordLocation separately; grouped
// writers reuse this population token with an immutable logical-root handle.
// Creation uses the same population token and revalidates logical absence at
// the original command time; expired/tombstone records need not stay physical.
// Physical coordinates are deliberately not a CAS token because GC may
// relocate the same value while preparation is suspended.
struct CompactWriteSnapshot {
  std::uint64_t index_generation_ = 0;
  std::uint64_t db_epoch_ = 0;
  std::uint64_t replication_epoch_ = 0;
};

// Bycorf frames guarantee ordinary allocation alignment, not cacheline
// alignment. This copied control state must remain safe inside such a frame.
static_assert(alignof(CompactWriteSnapshot) <= alignof(std::max_align_t));

}  // namespace keylane::storage
