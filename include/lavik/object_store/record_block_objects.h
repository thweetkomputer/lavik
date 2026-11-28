/*
 * Copyright (C) 2026 EloqData Inc.
 * SPDX-License-Identifier: Apache-2.0
 */
#pragma once

#include <array>
#include <string>

#include "absl/status/statusor.h"
#include "bycorf/runtime/task.h"
#include "lavik/storage/record_block_flush.h"

namespace lavik::object_store {

// A complete, contiguous image downloaded for one ordinary block allocation.
class RecordBlockImage {
 public:
  // Writes a caller-selected empty slot on an exclusively owned, freshly
  // formatted offline device. Call from a provisioning thread before cold
  // startup. Holds one block in memory and publishes the header last.
  absl::Status Install(const std::string& device,
                       std::uint32_t local_slot) const;

 private:
  template <typename Client>
  friend class RecordBlockObjects;
  std::array<std::byte, storage::kBlockHeaderSlotBytes> header_{};
  std::string records_;
};

// Worker-local writer for one source allocation and one fresh remote ID in
// an existing bucket/container. The owner serializes Upload calls, retains
// the client for their lifetime, and reserves the ID through restoration.
template <typename Client>
class RecordBlockObjects {
 public:
  RecordBlockObjects(const Client& client, std::uint64_t remote_block_id);
  RecordBlockObjects(const RecordBlockObjects&) = delete;
  RecordBlockObjects& operator=(const RecordBlockObjects&) = delete;

  // Publishes one flush. A timed-out PUT gets one retry with identical bytes.
  // The next boundary advances only after a successful service response. A
  // terminal service/transport failure stops this writer to preserve identity
  // when a remotely committed PUT may have lost its acknowledgement.
  bycorf::Task<absl::Status> Upload(storage::RecordBlockFlush flush);

  // Reads from a quiesced namespace, independently of any in-memory writer
  // state. Any missing interior fragment or invalid header fails the download.
  bycorf::Task<absl::StatusOr<RecordBlockImage>> Download() const;

 private:
  const Client& client_;
  std::string prefix_;
  std::uint64_t source_block_id_ = 0;
  storage::BlockHeader last_{};
  absl::Status failure_;
};

class S3Client;
class AzureBlobClient;
extern template class RecordBlockObjects<S3Client>;
extern template class RecordBlockObjects<AzureBlobClient>;
}  // namespace lavik::object_store
