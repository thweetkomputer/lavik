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

// Shared codecs for metadata value types that appear in more than one
// durable envelope. These functions own only the byte layout and decode-time
// field caps. Command validation and store-specific semantic invariants stay
// with their respective owners.

#include "absl/status/statusor.h"
#include "keylane/meta/commands.h"
#include "keylane/meta/encoding.h"

namespace keylane::meta {

void WriteActorContext(MetaWriter& writer, const ActorContext& actor);
absl::StatusOr<ActorContext> ReadActorContext(MetaReader& reader);

void WriteMetaDirectiveSpec(MetaWriter& writer,
                            const MetaDirectiveSpec& directive);
absl::StatusOr<MetaDirectiveSpec> ReadMetaDirectiveSpec(MetaReader& reader);

}  // namespace keylane::meta
