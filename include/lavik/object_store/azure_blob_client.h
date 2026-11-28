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

#include <map>
#include <string>
#include <string_view>
#include <vector>

#include "lavik/net/http_client.h"

namespace lavik::object_store {

// Azure endpoints address the account by host. Path-style emulators include
// the account in the request path as well.
enum class AzureAccountAddressing { kHost, kPath };

struct AzureBlobListPage {
  std::vector<std::string> keys_;
  // Opaque service marker. Empty marks the final page.
  std::string next_token_;
};

// Shared Key access to the block blobs in one container. Requests run on the
// calling Bycorf worker. The client must outlive all outstanding requests.
class AzureBlobClient {
 public:
  // Supply a resolved endpoint, account name and Base64 storage account key.
  // The endpoint owns the dial address, HTTP host and optional TLS context.
  static absl::StatusOr<AzureBlobClient> Create(
      net::HttpEndpoint endpoint, std::string account, std::string container,
      std::string_view base64_key,
      AzureAccountAddressing addressing = AzureAccountAddressing::kHost,
      net::HttpRequestOptions options = {});

  // Returns the opaque ETag for a successful write. Supply it verbatim to
  // conditionally replace a blob. A stale ETag returns FailedPrecondition.
  // Keep the binary payload immutable until the task completes.
  [[nodiscard]] bycorf::Task<absl::StatusOr<std::string>> Put(
      std::string key, std::string_view data, std::string if_match = {}) const;
  // Reads the blob bytes. A missing blob returns NotFound.
  [[nodiscard]] bycorf::Task<absl::StatusOr<std::string>> Get(
      std::string key) const;
  // Deletes one blob. A missing blob returns NotFound.
  [[nodiscard]] bycorf::Task<absl::Status> Delete(std::string key) const;
  // Reads one flat List Blobs page. Pass the marker back with the same prefix.
  [[nodiscard]] bycorf::Task<absl::StatusOr<AzureBlobListPage>> List(
      std::string prefix, std::string token = {},
      unsigned max_keys = 5000) const;

 private:
  AzureBlobClient(net::HttpEndpoint endpoint, std::string account,
                  std::string path, std::string key,
                  net::HttpRequestOptions options);
  bycorf::Task<absl::StatusOr<net::HttpResponse>> Send(
      net::HttpRequest request, unsigned expected,
      std::map<std::string, std::string> query = {}) const;

  net::HttpClient http_;
  std::string account_;
  std::string container_path_;
  std::string key_;
  net::HttpRequestOptions options_;
};

}  // namespace lavik::object_store
