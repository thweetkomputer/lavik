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

// MetaPopulationManifestStore owns immutable, content-addressed population
// documents. A group records freshness separately as
// (manifest_revision, manifest_digest); this store only answers what a digest
// means. That separation is what makes A -> B -> A observable while still
// deduplicating identical documents.

#include <cstdint>
#include <map>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

#include "absl/status/status.h"
#include "absl/status/statusor.h"
#include "lavik/meta/commands.h"
#include "lavik/meta/encoding.h"

namespace lavik::meta {

inline constexpr std::uint32_t kMaxMetaPopulationManifestEntries =
    kMetaSlotCount;
// A serialized document needs at least a digest and an empty-entry count.
// This decode-only ceiling is derived from the aggregate snapshot byte limit,
// rather than borrowing an unrelated operation-archive policy limit. Normal
// puts are governed by their exact remaining aggregate snapshot budget.
inline constexpr std::uint32_t kMaxMetaPopulationManifestsInSnapshot =
    static_cast<std::uint32_t>(kMaxMetaSnapshotBytes / (32u + 4u));

struct MetaPopulationManifestDocument {
  MetaHash256 manifest_digest_{};
  std::vector<MetaPopulationManifestEntry> entries_;
  bool operator==(const MetaPopulationManifestDocument&) const = default;
};

class MetaPopulationManifestStore {
 public:
  // Digest of the shared, domain-separated population-manifest encoding used
  // by both Meta projection and Data validation.
  static MetaHash256 CanonicalDigest(
      const std::vector<MetaPopulationManifestEntry>& entries);

  // Put is immutable and idempotent by digest. The command must already be
  // strictly sorted, contain only in-range partitions with nonzero logical
  // epochs, and its supplied digest must match its canonical bytes.
  absl::Status Put(const PutPopulationManifest& command);
  // Reference checks are aggregate-state concerns and happen in state_apply;
  // this primitive removes only an existing unreferenced document.
  absl::Status Prune(const PrunePopulationManifest& command);

  std::optional<MetaPopulationManifestDocument> Find(
      const MetaHash256& digest) const;
  bool Contains(const MetaHash256& digest) const;
  std::vector<MetaPopulationManifestDocument> Documents() const;
  std::size_t Size() const { return documents_.size(); }

  // Snapshot v1: schema_version u16, document count u32, then documents
  // sorted by digest. Each document stores its digest and sorted entries of
  // (partition u32, logical epoch u64). This store envelope is distinct from
  // the domain-separated canonical entry encoding hashed by CanonicalDigest.
  // Deserialize strictly enforces aggregate bytes, entry caps, sorting,
  // uniqueness, and digest agreement; violations fail stop.
  std::string Serialize() const;
  // Exact durable size without allocating or copying snapshot bytes.
  std::uint64_t SerializedSize() const;
  static absl::StatusOr<MetaPopulationManifestStore> Deserialize(
      std::string_view bytes);

 private:
  void WriteSnapshot(MetaWriter& writer) const;
  std::map<MetaHash256, MetaPopulationManifestDocument> documents_;
};

}  // namespace lavik::meta
