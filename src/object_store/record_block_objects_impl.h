/*
 * Copyright (C) 2026 EloqData Inc.
 * SPDX-License-Identifier: Apache-2.0
 */

#pragma once

#include <bitset>
#include <charconv>
#include <cstring>
#include <set>

#include "absl/strings/str_cat.h"
#include "lavik/object_store/record_block_objects.h"

namespace lavik::object_store {
namespace record_block_internal {
using namespace storage;

// A contiguous run starts with the first flush (sequence 1, offset 8192).
// Later headers describe the entire prefix, including earlier fragments.
inline absl::StatusOr<BlockHeader> NextHeader(
    const BlockHeader& last, std::uint32_t offset,
    std::span<const std::byte, kBlockHeaderSlotBytes> encoded,
    std::size_t data_size) {
  BlockHeader header;
  if (!DecodeBlockHeader(encoded, &header) ||
      header.kind_ != BlockKind::kRecords || offset != last.committed_bytes_ ||
      data_size == 0 || data_size % kDirectIoAlignment ||
      header.committed_bytes_ <= offset ||
      header.committed_bytes_ - offset != data_size ||
      header.header_sequence_ != last.header_sequence_ + 1 ||
      header.record_count_ <= last.record_count_ ||
      header.max_lsn_ < last.max_lsn_)
    return absl::DataLossError("invalid record block flush boundary or header");
  if (last.header_sequence_ &&
      (header.allocation_epoch_ != last.allocation_epoch_ ||
       header.writer_id_ != last.writer_id_ ||
       header.layout_worker_count_ != last.layout_worker_count_))
    return absl::DataLossError(
        "record block allocation changed between flushes");
  return header;
}
}  // namespace record_block_internal

template <typename Client>
RecordBlockObjects<Client>::RecordBlockObjects(const Client& client,
                                               std::uint64_t remote_block_id)
    : client_(client), prefix_(absl::StrCat(remote_block_id, "_")) {}

template <typename Client>
bycorf::Task<absl::Status> RecordBlockObjects<Client>::Upload(
    storage::RecordBlockFlush flush) {
  if (!failure_.ok()) co_return failure_;
  if (last_.header_sequence_ && source_block_id_ != flush.source_block_id_)
    co_return absl::FailedPreconditionError("remote block already assigned");
  auto header = record_block_internal::NextHeader(
      last_, flush.offset_, flush.header_, flush.data_.size());
  if (!header.ok()) co_return header.status();
  const auto key = absl::StrCat(prefix_, flush.offset_);
  std::string object(reinterpret_cast<const char*>(flush.header_.data()),
                     flush.header_.size());
  object.append(reinterpret_cast<const char*>(flush.data_.data()),
                flush.data_.size());
  auto written = co_await client_.Put(key, object);
  if (absl::IsDeadlineExceeded(written.status()))
    written = co_await client_.Put(key, object);
  if (!written.ok()) {
    failure_ = written.status();
    co_return failure_;
  }
  source_block_id_ = flush.source_block_id_;
  last_ = *header;
  co_return absl::OkStatus();
}

template <typename Client>
bycorf::Task<absl::StatusOr<RecordBlockImage>>
RecordBlockObjects<Client>::Download() const {
  // Decimal object keys list lexicographically. Each possible page boundary
  // takes one bit (256 bytes per block), independent of device count.
  std::bitset<storage::kStorageBlockBytes / storage::kDirectIoAlignment> starts;
  std::set<std::string> markers;
  std::string marker;
  do {
    auto page = co_await client_.List(prefix_, marker);
    if (!page.ok()) co_return page.status();
    for (std::string_view name : page->keys_) {
      if (!name.starts_with(prefix_))
        co_return absl::DataLossError("wrong block prefix");
      name.remove_prefix(prefix_.size());
      std::uint32_t offset = 0;
      auto [end, ec] =
          std::from_chars(name.data(), name.data() + name.size(), offset);
      if (ec != std::errc{} || end != name.data() + name.size() ||
          name.front() == '0' || offset < storage::kBlockHeaderBytes ||
          offset >= storage::kStorageBlockBytes ||
          offset % storage::kDirectIoAlignment)
        co_return absl::DataLossError("invalid flush object offset");
      auto index = offset / storage::kDirectIoAlignment;
      if (starts.test(index))
        co_return absl::DataLossError("duplicate flush object");
      starts.set(index);
    }
    marker = std::move(page->next_token_);
    if (!marker.empty() && !markers.insert(marker).second)
      co_return absl::DataLossError("cyclic flush object listing");
  } while (!marker.empty());
  if (starts.none())
    co_return absl::NotFoundError("no flush objects for block");

  RecordBlockImage image;
  storage::BlockHeader last;
  while (starts.any()) {
    const auto offset = last.committed_bytes_;
    auto index = offset / storage::kDirectIoAlignment;
    if (index >= starts.size() || !starts.test(index))
      co_return absl::DataLossError("gap or overlap in record block flushes");
    starts.reset(index);
    auto object = co_await client_.Get(absl::StrCat(prefix_, offset));
    if (!object.ok()) co_return object.status();
    if (object->size() < image.header_.size())
      co_return absl::DataLossError("truncated flush object");
    std::memcpy(image.header_.data(), object->data(), image.header_.size());
    std::string_view data(*object);
    data.remove_prefix(image.header_.size());
    auto header = record_block_internal::NextHeader(last, offset, image.header_,
                                                    data.size());
    if (!header.ok()) co_return header.status();
    image.records_.append(data);
    last = *header;
  }
  co_return image;
}

}  // namespace lavik::object_store
