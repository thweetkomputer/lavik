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

module;
#include "lavik/storage/foundation_dependencies.h"

export module lavik.storage.foundation;

#if defined(LAVIK_IMPORT_STD)
import std;
#endif

// Keep these existing types in the global C++ ABI: non-storage libraries
// still define their out-of-line functions. Export the
// definitions themselves so consumers can use them without reparsing headers.
#define LAVIK_BUILDING_STORAGE_FOUNDATION 1
export extern "C++" {
// These headers omit includes in the provider, so retain dependency order.
// clang-format off
#include "lavik/memory.h"
#include "lavik/retained_allocator.h"
#include "lavik/containers/cow_array.h"
#include "lavik/local_shared_ptr.h"
#include "lavik/containers/cow_map.h"
#include "lavik/containers/fenwick_tree.h"
#include "lavik/storage/detail/collection_limits.h"
#include "lavik/storage/format.h"
#include "lavik/storage/detail/hash_codec.h"
#include "lavik/storage/scan_hash_map.h"
#include "lavik/storage/detail/grouped/hash.h"
#include "lavik/storage/detail/grouped/collection.h"
#include "lavik/storage/detail/grouped/commit.h"
#include "lavik/storage/detail/record_index.h"
#include "lavik/storage/detail/grouped/object_index.h"
  // clang-format on
}
