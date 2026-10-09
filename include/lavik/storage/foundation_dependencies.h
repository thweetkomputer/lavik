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

// External prerequisites are parsed in the global module fragment. The
// foundation provider exports the project definitions in dependency order;
// its headers skip their textual includes while that provider is built.

#include <mimalloc.h>

#if defined(LAVIK_IMPORT_STD)
#include "lavik/std_import.h"
#else
#include <algorithm>
#endif
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
#if defined(LAVIK_IMPORT_STD)
#include "lavik/std_import.h"
#else
#include <bit>
#endif
#include <cassert>
#if defined(LAVIK_IMPORT_STD)
#include "lavik/std_import.h"
#else
#include <compare>
#endif
#include <cstddef>
#include <cstdint>
#include <cstring>
#if defined(LAVIK_IMPORT_STD)
#include "lavik/std_import.h"
#else
#include <exception>
#endif
#if defined(LAVIK_IMPORT_STD)
#include "lavik/std_import.h"
#else
#include <functional>
#endif
#if defined(LAVIK_IMPORT_STD)
#include "lavik/std_import.h"
#else
#include <iterator>
#endif
#if defined(LAVIK_IMPORT_STD)
#include "lavik/std_import.h"
#else
#include <limits>
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
#include <new>
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
#include <stdexcept>
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
#include <thread>
#endif
#if defined(LAVIK_IMPORT_STD)
#include "lavik/std_import.h"
#else
#include <type_traits>
#endif
#if defined(LAVIK_IMPORT_STD)
#include "lavik/std_import.h"
#else
#include <utility>
#endif
#if defined(LAVIK_IMPORT_STD)
#include "lavik/std_import.h"
#else
#include <variant>
#endif
#if defined(LAVIK_IMPORT_STD)
#include "lavik/std_import.h"
#else
#include <vector>
#endif

#include "absl/container/flat_hash_set.h"
#include "absl/container/inlined_vector.h"
#include "absl/functional/function_ref.h"
#include "absl/numeric/int128.h"
#include "absl/status/status.h"
#include "absl/status/statusor.h"

#if defined(__SSE2__)
#include <emmintrin.h>
#elif defined(__ARM_NEON)
#include <arm_neon.h>
#endif
