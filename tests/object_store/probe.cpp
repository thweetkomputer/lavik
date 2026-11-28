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

#include <charconv>
#include <cstdint>
#include <iostream>
#include <string>

#include "absl/strings/escaping.h"
#include "bycorf/runtime/runtime.h"
#include "lavik/net/http_client.h"
#include "lavik/object_store/azure_blob_client.h"
#include "lavik/object_store/s3_client.h"

namespace {
struct Endpoint {
  bool azure;
  std::uint16_t port;
  std::string container, account, secret;
};

std::string TestPayload() {
  std::string data(1024 * 1024 + 37, '\0');
  for (std::size_t i = 0; i < data.size(); ++i)
    data[i] = static_cast<char>(i % 256);
  return data;
}

template <typename Client>
bycorf::Task<absl::Status> RoundTrip(const Client& client,
                                     const Client& limited,
                                     const Client& invalid) {
  const std::string prefix = "blocks/空 格+%&/";
  const std::string first = prefix + "1001_0";
  const std::string second = prefix + "1001_8192";
  const auto bytes = TestPayload();
  auto tag = co_await client.Put(first, bytes);
  if (!tag.ok()) co_return tag.status();
  auto get = co_await client.Get(first);
  if (!get.ok()) co_return get.status();
  if (*get != bytes) co_return absl::DataLossError("binary GET mismatch");
  const std::string replacement("new\0bytes", 9);
  auto overwrite = co_await client.Put(first, replacement, *tag);
  if (!overwrite.ok()) co_return overwrite.status();
  auto too_large = co_await limited.Get(first);
  if (!absl::IsResourceExhausted(too_large.status()))
    co_return absl::DataLossError("GET ignored its response body limit");
  auto stale = co_await limited.Put(first, bytes, *tag);
  if (!absl::IsFailedPrecondition(stale.status()))
    co_return absl::DataLossError(
        "stale If-Match did not return FailedPrecondition");
  get = co_await client.Get(first);
  if (!get.ok()) co_return get.status();
  if (*get != replacement)
    co_return absl::DataLossError("conditional overwrite mismatch");

  auto other = co_await client.Put("another-prefix", "");
  if (!other.ok()) co_return other.status();
  auto empty = co_await client.Put(second, "");
  if (!empty.ok()) co_return empty.status();
  auto page = co_await client.List(prefix, "", 1);
  if (!page.ok()) co_return page.status();
  if (page->keys_.size() != 1 || page->keys_[0] != first ||
      page->next_token_.empty())
    co_return absl::DataLossError("unexpected first page");
  page = co_await client.List(prefix, page->next_token_, 1);
  if (!page.ok()) co_return page.status();
  if (page->keys_.size() != 1 || page->keys_[0] != second)
    co_return absl::DataLossError("unexpected second page");
  // A service can return a marker at an exact page boundary.
  if (!page->next_token_.empty()) {
    page = co_await client.List(prefix, page->next_token_, 1);
    if (!page.ok()) co_return page.status();
    if (!page->keys_.empty() || !page->next_token_.empty())
      co_return absl::DataLossError("unexpected trailing page");
  }

  auto denied = co_await invalid.Get(first);
  if (!absl::IsPermissionDenied(denied.status()))
    co_return absl::DataLossError(
        "invalid signature did not return PermissionDenied");
  auto removed = co_await client.Delete(first);
  if (!removed.ok()) co_return removed;
  get = co_await limited.Get(first);
  if (!absl::IsNotFound(get.status()))
    co_return absl::DataLossError("GET after delete did not return NotFound");
  co_return absl::OkStatus();
}

bycorf::Task<absl::Status> Run(bycorf::Worker& worker, const Endpoint& endpoint,
                               absl::Status& result) {
  using namespace lavik::object_store;
  lavik::net::HttpEndpoint host{.address_ = "127.0.0.1",
                                .port_ = endpoint.port};
  lavik::net::HttpRequestOptions limited_options{.max_response_body_bytes_ = 0};
  if (endpoint.azure) {
    // Exercise both resource signatures against the same account. Dial
    // loopback directly even when the HTTP Host selects host-style routing.
    auto limited = AzureBlobClient::Create(
        host, endpoint.account, endpoint.container, endpoint.secret,
        AzureAccountAddressing::kPath, limited_options);
    host.host_ = endpoint.account + ".blob.localhost";
    auto client = AzureBlobClient::Create(host, endpoint.account,
                                          endpoint.container, endpoint.secret);
    auto invalid =
        AzureBlobClient::Create(host, endpoint.account, endpoint.container,
                                absl::Base64Escape("wrong key"));
    if (!client.ok())
      result = client.status();
    else if (!limited.ok())
      result = limited.status();
    else if (!invalid.ok())
      result = invalid.status();
    else
      result = co_await RoundTrip(*client, *limited, *invalid);
  } else {
    S3Credentials credentials{endpoint.account, endpoint.secret};
    S3Client client(host, "us-east-1", endpoint.container, credentials);
    S3Client limited(host, "us-east-1", endpoint.container, credentials,
                     limited_options);
    credentials.secret_key_ += "invalid";
    S3Client invalid(host, "us-east-1", endpoint.container,
                     std::move(credentials));
    result = co_await RoundTrip(client, limited, invalid);
  }
  worker.RequestStop();
  co_return absl::OkStatus();
}
}  // namespace

int main(int argc, char** argv) {
  Endpoint endpoint{};
  if (argc != 3) return 2;
  const std::string_view provider(argv[1]), port(argv[2]);
  if (provider != "azure" && provider != "s3") return 2;
  endpoint.azure = provider == "azure";
  const auto [end, ec] =
      std::from_chars(port.begin(), port.end(), endpoint.port);
  if (ec != std::errc{} || end != port.end() || !endpoint.port) return 2;
  // Receive fixture credentials over stdin before starting the worker.
  for (auto* field : {&endpoint.container, &endpoint.account, &endpoint.secret})
    if (!std::getline(std::cin, *field) || field->empty()) return 2;
  bycorf::Runtime runtime;
  absl::Status result;
  runtime.Start(
      1,
      [&](unsigned, bycorf::Worker& worker) {
        bycorf::WorkerOptions options;
        options.recv_buffer_count_ = 0;
        result = worker.Init(options);
        if (!result.ok()) return 1;
        worker.Spawn(Run(worker, endpoint, result));
        worker.Run();
        worker.Shutdown();
        worker.DestroyDetachedTasks();
        return result.ok() ? 0 : 1;
      },
      false);
  runtime.WaitUntilStopped();
  if (!result.ok()) std::cerr << result << '\n';
  return runtime.exit_code();
}
