/*
 * Copyright (C) 2026 EloqData Inc.
 * SPDX-License-Identifier: Apache-2.0
 */

#include <map>
#include <vector>

#include "gtest/gtest.h"
#include "record_block_objects_impl.h"

namespace lavik::object_store {
namespace {
using namespace storage;

struct MemoryStore {
  mutable std::vector<std::pair<std::string, std::string>> puts;
  mutable int timeouts = 0;
  bycorf::Task<absl::StatusOr<std::string>> Put(std::string key,
                                                std::string_view bytes) const {
    puts.emplace_back(std::move(key), bytes);
    if (timeouts > 0) {
      --timeouts;
      co_return absl::DeadlineExceededError("committed, acknowledgement lost");
    }
    co_return std::string("etag");
  }
};

template <class T>
T RunImmediate(bycorf::Task<T> task) {
  auto handle = std::move(task).ReleaseHandle();
  bycorf::Task<T> owner(handle);
  handle.resume();
  return std::move(owner).TakeResult();
}

TEST(RecordBlockObjects, RetriesSameObjectAndAdvancesAfterAcknowledgement) {
  MemoryStore store;
  store.timeouts = 1;
  RecordBlockObjects writer(store, 1001);
  std::array<std::byte, kBlockHeaderSlotBytes> encoded;
  std::array<std::byte, kDirectIoAlignment> data{};
  RecordBlockFlush flush{91, kBlockHeaderBytes, encoded, data};
  BlockHeader header{.allocation_epoch_ = 7,
                     .committed_bytes_ = kBlockHeaderBytes + kDirectIoAlignment,
                     .record_count_ = 1,
                     .header_sequence_ = 1,
                     .layout_worker_count_ = 1};
  EncodeBlockHeader(header, encoded);
  ASSERT_TRUE(RunImmediate(writer.Upload(flush)).ok());
  ASSERT_EQ(store.puts.size(), 2u);
  EXPECT_EQ(store.puts[0], store.puts[1]);
  EXPECT_EQ(store.puts[0].first, "1001_8192");

  flush.offset_ = header.committed_bytes_;
  header.committed_bytes_ += kDirectIoAlignment;
  ++header.record_count_;
  ++header.header_sequence_;
  // A valid CRC from another allocation cannot extend this object chain.
  ++header.allocation_epoch_;
  EncodeBlockHeader(header, encoded);
  EXPECT_TRUE(absl::IsDataLoss(RunImmediate(writer.Upload(flush))));
  EXPECT_EQ(store.puts.size(), 2u);
  --header.allocation_epoch_;
  EncodeBlockHeader(header, encoded);
  ASSERT_TRUE(RunImmediate(writer.Upload(flush)).ok());
  EXPECT_EQ(store.puts.back().first, "1001_12288");
}

TEST(RecordBlockObjects, AmbiguousFailureStopsLaterWrites) {
  MemoryStore store;
  store.timeouts = 2;
  RecordBlockObjects writer(store, 1001);
  std::array<std::byte, kBlockHeaderSlotBytes> encoded;
  std::array<std::byte, kDirectIoAlignment> data{};
  EncodeBlockHeader({.allocation_epoch_ = 1,
                     .committed_bytes_ = kBlockHeaderBytes + kDirectIoAlignment,
                     .record_count_ = 1,
                     .header_sequence_ = 1,
                     .layout_worker_count_ = 1},
                    encoded);
  RecordBlockFlush flush{1, kBlockHeaderBytes, encoded, data};
  EXPECT_TRUE(absl::IsDeadlineExceeded(RunImmediate(writer.Upload(flush))));
  data[0] = std::byte{1};
  EXPECT_TRUE(absl::IsDeadlineExceeded(RunImmediate(writer.Upload(flush))));
  EXPECT_EQ(store.puts.size(), 2u);
}
// Return one key per page in service (lexical) order.
struct PagedStore {
  struct Page {
    std::vector<std::string> keys_;
    std::string next_token_;
  };
  std::map<std::string, std::string> objects;
  bycorf::Task<absl::StatusOr<Page>> List(std::string_view,
                                          const std::string& marker) const {
    auto it = marker.empty() ? objects.begin() : objects.upper_bound(marker);
    Page page;
    if (it != objects.end()) {
      page.keys_.push_back(it->first);
      if (std::next(it) != objects.end()) page.next_token_ = it->first;
    }
    co_return page;
  }
  bycorf::Task<absl::StatusOr<std::string>> Get(const std::string& key) const {
    co_return objects.at(key);
  }
};

TEST(RecordBlockObjects, ValidatesLengthsAndAllocationAcrossListPages) {
  PagedStore store;
  RecordBlockObjects reader(store, 1001);
  BlockHeader header{.allocation_epoch_ = 5,
                     .committed_bytes_ = kBlockHeaderBytes + kDirectIoAlignment,
                     .record_count_ = 1,
                     .header_sequence_ = 1,
                     .layout_worker_count_ = 1};
  auto object = [&] {
    std::array<std::byte, kBlockHeaderSlotBytes> slot;
    EncodeBlockHeader(header, slot);
    std::string result(reinterpret_cast<const char*>(slot.data()), slot.size());
    result.append(kDirectIoAlignment, 'x');
    return result;
  };
  store.objects["1001_8192"] = object();
  ++header.header_sequence_;
  ++header.record_count_;
  header.committed_bytes_ += kDirectIoAlignment;
  auto& second = store.objects["1001_12288"];
  second = object();
  auto complete = RunImmediate(reader.Download());
  ASSERT_TRUE(complete.ok()) << complete.status();
  second.pop_back();
  EXPECT_TRUE(absl::IsDataLoss(RunImmediate(reader.Download()).status()));
  ++header.allocation_epoch_;
  second = object();
  EXPECT_TRUE(absl::IsDataLoss(RunImmediate(reader.Download()).status()));
}
}  // namespace
}  // namespace lavik::object_store
