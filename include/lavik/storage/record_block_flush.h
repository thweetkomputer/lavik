/*
 * Copyright (C) 2026 EloqData Inc.
 * SPDX-License-Identifier: Apache-2.0
 */

#pragma once

#include "lavik/storage/format.h"

namespace lavik::storage {

// One immutable ordinary-block flush. Both spans borrow the pinned staging
// buffer until the asynchronous consumer completes. offset_ starts after A/B.
struct RecordBlockFlush {
  std::uint64_t source_block_id_;
  std::uint32_t offset_;
  std::span<const std::byte, kBlockHeaderSlotBytes> header_;
  std::span<const std::byte> data_;
};

}  // namespace lavik::storage
