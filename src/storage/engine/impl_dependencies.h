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

#include <fcntl.h>
#include <linux/fs.h>

#include "lavik/storage/engine.h"
#ifdef BLOCK_SIZE
#undef BLOCK_SIZE
#endif
#include <sys/ioctl.h>
#include <sys/random.h>
#include <sys/stat.h>
#include <unistd.h>

#include <cassert>
#include <cerrno>
#include <cstdlib>
#include <cstring>

#include "../../replication/log_block.h"
#include "../ring_buffer.h"
#include "absl/container/flat_hash_map.h"
#include "absl/container/flat_hash_set.h"
#include "bycorf/io/spdk_storage.h"
#include "bycorf/io/storage.h"
#include "bycorf/runtime/concurrentqueue.h"
#include "bycorf/runtime/cross_core.h"
#include "bycorf/runtime/sync.h"
#include "bycorf/runtime/worker.h"
#include "lavik/fault_injection.h"
#include "lavik/memory.h"
#include "lavik/replication_history.h"
#include "lavik/std_import.h"
#include "lavik/storage/detail/compact_write.h"
#include "lavik/storage/detail/grouped/object_index.h"
#include "lavik/storage/detail/hash_codec.h"
#include "lavik/storage/detail/record_index.h"
#include "lavik/storage/detail/record_payload_cursor.h"
#include "lavik/storage/detail/replica_collection_stage.h"
#include "lavik/storage/detail/tx_block_leases.h"
#include "lavik/storage/format.h"
#include "lavik/storage/scan_hash_map.h"
#include "lavik/tx/tx_shard.h"
#include "recovery_allocator.h"
#include "spdlog/spdlog.h"
