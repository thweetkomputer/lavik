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

#include "absl/time/time.h"
#include "lavik/object_store/azure_blob_client.h"

namespace lavik::object_store::internal {

// target_ contains the encoded path, headers_ may contain If-Match. Encodes
// query values for transmission and signs their original values.
absl::Status SignAzureRequest(net::HttpRequest& request,
                              const std::map<std::string, std::string>& query,
                              std::string_view account,
                              std::string_view decoded_key, absl::Time now);
absl::StatusOr<AzureBlobListPage> ParseAzureListPage(
    std::string_view body, std::string_view previous_marker, unsigned max_keys);
}  // namespace lavik::object_store::internal
