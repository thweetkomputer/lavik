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

#include "lavik/pch.h"

// Private to the Data library and its executable: cache the large storage
// declaration graph once instead of reparsing it in each translation unit.
// Keep this out of the public PCH so other targets do not inherit engine
// internals. Editing a header in this set invalidates the whole Data PCH.
#include "storage/engine/impl.h"

// Include the common storage helpers explicitly so their template definitions
// are cached even when they are not transitively included by impl.h.
#include "absl/container/flat_hash_map.h"
#include "absl/container/flat_hash_set.h"
#include "absl/container/inlined_vector.h"
#include "absl/hash/hash.h"
#include "absl/strings/cord.h"
#include "absl/strings/str_cat.h"
#include "lavik/fault_pause.h"
#include "lavik/glob.h"
#include "lavik/memory.h"
#include "lavik/metrics.h"
#include "lavik/random_sample.h"
#include "lavik/redis_parse.h"
#include "lavik/replication_command.h"
#include "lavik/storage/detail/collection_compact_stream.h"
#include "lavik/storage/detail/collection_ingest_budget.h"
#include "lavik/storage/detail/grouped/scratch.h"
#include "lavik/storage/detail/grouped/sorted_rewrite.h"
#include "lavik/storage/detail/hash_read.h"
#include "lavik/storage/detail/ordered_compact_codec.h"
#include "lavik/storage/detail/stream_records.h"
#include "lavik/storage/engine.h"
#include "storage/engine/device_affinity.h"
#include "storage/engine/grouped/dependency_guard.h"
#include "storage/engine/grouped/dependency_test_hook.h"
