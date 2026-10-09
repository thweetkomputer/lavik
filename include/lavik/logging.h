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

#include <cstddef>
#include <string>

#include "absl/status/status.h"

namespace lavik {

struct LoggingOptions {
  std::string log_dir_{"./logs"};
  std::size_t max_log_size_mb_ = 100;
  std::size_t max_log_files_ = 10;
  bool log_to_stderr_ = false;
  bool also_log_to_stderr_ = false;
};

// Validates values shared by config-file, command-line, and direct callers.
absl::Status ValidateLoggingOptions(const LoggingOptions& options);

// Installs Lavik's synchronous spdlog logger as the process-wide default.
absl::Status InitializeLogging(const LoggingOptions& options);

// Flushes and releases all spdlog resources owned by the process registry.
void ShutdownLogging();

}  // namespace lavik
