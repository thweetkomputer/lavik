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

#include "lavik/storage/detail/hash_read.h"

#include <algorithm>
#include <cassert>
#include <limits>
#include <string>

#include "lavik/memory.h"
#include "lavik/storage/detail/hash_codec.h"
#include "lavik/storage/engine.h"

namespace lavik::storage {

absl::StatusOr<std::optional<std::string_view>> FindHashGroupField(
    std::string_view payload, std::uint32_t field_count,
    std::string_view field) {
  // DecodeHashGroupMetadata already checked the empty-group representation
  // and the minimum payload length. Only the inner encoding remains unchecked.
  if (field_count == 0) return std::nullopt;
  auto reader = HashValueReader::Open(payload.substr(kHashGroupHeaderBytes));
  if (!reader.ok()) [[unlikely]]
    return absl::DataLossError(reader.status().message());
  if (reader->size() != field_count) [[unlikely]]
    return absl::DataLossError(
        "Hash group inner count disagrees with envelope");

  std::optional<std::string_view> matched;
  // Consume even the entries after a match: Next checks trailing bytes on the
  // last entry, and a later occurrence of the requested field is corruption.
  // Find(field) already checked the requested field's route using the persisted
  // seed. Unrelated fields need neither copying nor digest reconstruction.
  for (std::size_t i = 0; i < reader->size(); ++i) {
    auto entry = reader->Next();
    if (!entry.ok()) [[unlikely]]
      return absl::DataLossError(entry.status().message());
    if (entry->field_ != field) continue;
    if (matched.has_value()) [[unlikely]]
      return absl::DataLossError("duplicate Hash field in group");
    matched = entry->value_;
  }
  return matched;
}

absl::Status FindHashGroupFields(std::string_view payload,
                                 std::uint32_t field_count,
                                 std::span<HashFieldLookup> requests) {
  for (auto& request : requests) request.value_.reset();
  if (field_count == 0) return absl::OkStatus();
  auto reader = HashValueReader::Open(payload.substr(kHashGroupHeaderBytes));
  if (!reader.ok()) [[unlikely]]
    return absl::DataLossError(reader.status().message());
  if (reader->size() != field_count) [[unlikely]]
    return absl::DataLossError(
        "Hash group inner count disagrees with envelope");
  for (std::size_t i = 0; i < reader->size(); ++i) {
    auto entry = reader->Next();
    if (!entry.ok()) [[unlikely]]
      return absl::DataLossError(entry.status().message());
    // Binary search avoids hashing every unrelated encoded field. The sorted
    // request views also keep duplicate operands adjacent without owning names.
    auto match = std::lower_bound(
        requests.begin(), requests.end(), entry->field_,
        [](const HashFieldLookup& request, std::string_view field) {
          return request.field_ < field;
        });
    if (match == requests.end() || match->field_ != entry->field_) continue;
    if (match->value_) [[unlikely]]
      return absl::DataLossError("duplicate Hash field in group");
    for (; match != requests.end() && match->field_ == entry->field_; ++match)
      match->value_ = entry->value_;
  }
  return absl::OkStatus();
}

absl::Status RetainHashGroupValues(HashResult& result,
                                   std::span<const HashFieldLookup> requests) {
  std::size_t retained = 0;
  for (const auto& request : requests) {
    if (!request.value_) continue;
    const auto bytes =
        std::max(request.value_->size(), std::string{}.capacity()) + 1;
    if (bytes > std::numeric_limits<std::size_t>::max() - retained)
        [[unlikely]] {
      RecordMemoryRejection();
      return absl::ResourceExhaustedError("OOM Hash output is too large");
    }
    retained += bytes;
  }
  if (retained == 0) return absl::OkStatus();
  if (retained > std::numeric_limits<std::size_t>::max() -
                     result.retained_charge_.bytes()) [[unlikely]] {
    RecordMemoryRejection();
    return absl::ResourceExhaustedError("OOM Hash output is too large");
  }
  auto reservation = TryReserveMemory(retained);
  if (!reservation) [[unlikely]] {
    RecordMemoryRejection();
    return absl::ResourceExhaustedError("OOM Hash output retention");
  }
  retained = 0;
  for (const auto& request : requests) {
    if (!request.value_) continue;
    auto& value = result.values_[request.result_index_];
    assert(!value);
    value.emplace(*request.value_);
    const auto bytes = value->capacity() + 1;
    if (bytes > reservation->bytes() - retained) [[unlikely]] {
      RecordMemoryRejection();
      return absl::ResourceExhaustedError("OOM Hash output retention");
    }
    retained += bytes;
  }
  // Growth is covered by the still-live reservation. Its destructor releases
  // pending admission after the existing output owner takes over the bytes.
  result.retained_charge_.Resize(result.retained_charge_.bytes() + retained);
  return absl::OkStatus();
}

absl::Status RetainHashLookupValue(HashResult& result,
                                   std::optional<std::string_view> matched) {
  assert(result.values_.capacity() == 0 &&
         result.retained_charge_.bytes() == 0);
  std::size_t retained =
      sizeof(HashResult) + sizeof(std::optional<std::string>);
  if (matched)
    retained += std::max(matched->size(), std::string{}.capacity()) + 1;
  auto reservation = TryReserveMemory(retained);
  if (!reservation) [[unlikely]] {
    RecordMemoryRejection();
    return absl::ResourceExhaustedError("OOM Hash output retention");
  }
  // Reserve before copying out of the page lease, then check actual capacities
  // before transferring admission to the result. Match other Hash results'
  // conservative SSO accounting; a missing field still owns one vector slot.
  if (matched)
    result.values_.emplace_back(std::in_place, *matched);
  else
    result.values_.emplace_back(std::nullopt);
  retained = sizeof(HashResult) +
             result.values_.capacity() * sizeof(result.values_[0]);
  if (matched) retained += result.values_[0]->capacity() + 1;
  if (retained > reservation->bytes()) [[unlikely]] {
    RecordMemoryRejection();
    return absl::ResourceExhaustedError("OOM Hash output retention");
  }
  result.retained_charge_.Adopt(&*reservation, retained);
  return absl::OkStatus();
}

}  // namespace lavik::storage
