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

// Canonical byte format shared by the Meta authority that persists population
// manifests and the Data plane that validates and executes them. Keeping the
// encoding below both planes prevents a digest accepted by Meta from naming
// different content, or no valid content, at a Data node.

#include <cstddef>
#include <cstdint>
#include <span>
#include <string>
#include <string_view>

namespace lavik {

inline constexpr std::string_view kPopulationManifestDigestDomain =
    "LAVIK_POPULATION_V1";
inline constexpr std::uint16_t kPopulationManifestDigestSchemaVersion = 1;

// A plane-neutral entry used only to produce a manifest's content identity.
// Callers validate the 16,384-partition domain and canonical ordering before
// treating the resulting digest as authoritative.
struct PopulationManifestDigestEntry {
  std::uint32_t partition_id_ = 0;
  std::uint64_t logical_epoch_ = 0;
};

// Encodes the bytes covered by the population-manifest SHA-256 identity:
//
//   domain || u16be(schema_version) || u32be(entry_count) ||
//   repeated(u16be(partition_id) || u64be(logical_epoch))
//
// Entries are not sorted here because both planes must reject non-canonical
// durable input rather than silently assigning it a different identity.
inline std::string EncodePopulationManifestDigestInput(
    std::span<const PopulationManifestDigestEntry> entries) {
  std::string encoded;
  encoded.reserve(kPopulationManifestDigestDomain.size() + 2 + 4 +
                  entries.size() * (2 + 8));
  encoded.append(kPopulationManifestDigestDomain);

  const auto append_be = [&encoded](std::uint64_t value, std::size_t bytes) {
    for (std::size_t remaining = bytes; remaining != 0; --remaining) {
      encoded.push_back(static_cast<char>(value >> ((remaining - 1) * 8)));
    }
  };
  append_be(kPopulationManifestDigestSchemaVersion, 2);
  append_be(static_cast<std::uint32_t>(entries.size()), 4);
  for (const PopulationManifestDigestEntry& entry : entries) {
    append_be(static_cast<std::uint16_t>(entry.partition_id_), 2);
    append_be(entry.logical_epoch_, 8);
  }
  return encoded;
}

}  // namespace lavik
