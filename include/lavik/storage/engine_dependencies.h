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

#if defined(LAVIK_IMPORT_STD)
#include "lavik/std_import.h"
#else
#include <array>
#endif
#if defined(LAVIK_IMPORT_STD)
#include "lavik/std_import.h"
#else
#include <atomic>
#endif
#include <cassert>
#if defined(LAVIK_IMPORT_STD)
#include "lavik/std_import.h"
#else
#include <chrono>
#endif
#if defined(LAVIK_IMPORT_STD)
#include "lavik/std_import.h"
#else
#include <coroutine>
#endif
#include <cstddef>
#include <cstdint>
#if defined(LAVIK_IMPORT_STD)
#include "lavik/std_import.h"
#else
#include <functional>
#endif
#if defined(LAVIK_IMPORT_STD)
#include "lavik/std_import.h"
#else
#include <map>
#endif
#if defined(LAVIK_IMPORT_STD)
#include "lavik/std_import.h"
#else
#include <memory>
#endif
#if defined(LAVIK_IMPORT_STD)
#include "lavik/std_import.h"
#else
#include <optional>
#endif
#if defined(LAVIK_IMPORT_STD)
#include "lavik/std_import.h"
#else
#include <span>
#endif
#if defined(LAVIK_IMPORT_STD)
#include "lavik/std_import.h"
#else
#include <string>
#endif
#if defined(LAVIK_IMPORT_STD)
#include "lavik/std_import.h"
#else
#include <string_view>
#endif
#if defined(LAVIK_IMPORT_STD)
#include "lavik/std_import.h"
#else
#include <vector>
#endif

#include "absl/status/statusor.h"
#include "bycorf/runtime/task.h"
#include "lavik/lease_deadline.h"
#include "lavik/memory.h"
#include "lavik/read_trace.h"
#include "lavik/set_trace.h"
#include "lavik/storage/buffer_pool.h"
#include "lavik/storage/collection_page.h"
#include "lavik/storage/format.h"
#include "lavik/storage/sorted_set.h"

namespace bycorf {
class Worker;
}  // namespace bycorf

namespace lavik {
class ReplicationHistory;
}

namespace lavik::storage {
struct GroupedCommitDecision;
struct GroupedCommitDependency;
class ExpirationAuthorityTestPeer;
class TombRaiderTestPeer;
}  // namespace lavik::storage
