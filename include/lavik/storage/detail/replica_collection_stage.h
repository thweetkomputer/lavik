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

#include <optional>

#include "lavik/memory.h"
#include "lavik/storage/detail/collection_compact_stream.h"
#include "lavik/storage/engine.h"
#include "lavik/tx/tx_shard.h"

namespace lavik::storage {

// A native full-sync target keeps this state on the partition owner across
// transport frames. The key hold prevents observing an intermediate root;
// the outer decision independently prevents accepting it after a crash.
// Destruction is not an abort operation: callers must settle the undo/decision
// before releasing the stage, even when a transport/session is cancelled.
struct ReplicaCollectionStage {
  RetainedMemoryCharge decoded_charge_;
  RetainedMemoryCharge undo_charge_;
  std::optional<CollectionCompactDecoder> decoder_;
  TxShardWrites writes_;
  tx::TxShard::Guard key_hold_;
  std::uint64_t received_bytes_ = 0;
  std::uint64_t applied_count_ = 0;
  std::size_t undo_overhead_bytes_ = 0;
  bool skip_ = false;
  bool settled_ = false;
};

}  // namespace lavik::storage
