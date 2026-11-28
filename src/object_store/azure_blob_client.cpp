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

#include "lavik/object_store/azure_blob_client.h"

#include <libxml/parser.h>
#include <openssl/hmac.h>

#include <algorithm>
#include <climits>
#include <memory>

#include "absl/strings/ascii.h"
#include "absl/strings/escaping.h"
#include "absl/strings/str_cat.h"
#include "absl/strings/str_join.h"
#include "absl/time/clock.h"
#include "azure_blob_protocol.h"
#include "protocol_common.h"

namespace lavik::object_store {
namespace {
using net::HttpMethod;
using net::HttpRequest;
using net::HttpResponse;

}  // namespace

absl::Status internal::SignAzureRequest(
    HttpRequest& request, const std::map<std::string, std::string>& query,
    std::string_view account, std::string_view decoded_key, absl::Time now) {
  // The Blob Shared Key scheme uses fixed slots even for omitted headers.
  // Content-Length zero signs as empty for service versions since 2015-02-21.
  const auto length =
      request.body_.empty() ? "" : absl::StrCat(request.body_.size());
  std::string_view fields[12]{};
  fields[0] = net::MethodName(request.method_);
  fields[3] = length;
  for (const auto& header : request.headers_) {
    if (header.name_ == "if-match") fields[8] = header.value_;
  }
  std::string signed_text = absl::StrJoin(fields, "\n");
  signed_text += '\n';

  // Keep the x-ms fields in lexical order on the wire and in the signature.
  auto add_header = [&](std::string name, std::string value) {
    absl::StrAppend(&signed_text, name, ":", value, "\n");
    request.headers_.push_back({std::move(name), std::move(value)});
  };
  if (request.method_ == HttpMethod::kPut)
    add_header("x-ms-blob-type", "BlockBlob");
  add_header("x-ms-date", absl::FormatTime("%a, %d %b %Y %H:%M:%S GMT", now,
                                           absl::UTCTimeZone()));
  add_header("x-ms-version", "2023-11-03");
  absl::StrAppend(&signed_text, "/", account, request.target_);
  std::string_view separator = "?";
  for (const auto& [name, value] : query) {
    absl::StrAppend(&signed_text, "\n", name, ":", value);
    absl::StrAppend(&request.target_, separator, name, "=", Encode(value));
    separator = "&";
  }
  unsigned char signature[32];
  if (decoded_key.size() > INT_MAX ||
      !HMAC(EVP_sha256(), decoded_key.data(),
            static_cast<int>(decoded_key.size()),
            reinterpret_cast<const unsigned char*>(signed_text.data()),
            signed_text.size(), signature, nullptr))
    return absl::InternalError("Azure Shared Key HMAC-SHA256 failed");
  request.headers_.push_back(
      {"Authorization",
       absl::StrCat(
           "SharedKey ", account, ":",
           absl::Base64Escape(std::string_view(
               reinterpret_cast<const char*>(signature), sizeof(signature))))});
  return absl::OkStatus();
}

absl::StatusOr<AzureBlobListPage> internal::ParseAzureListPage(
    std::string_view body, std::string_view previous_marker,
    unsigned max_keys) {
  if (body.size() > INT_MAX)
    return absl::ResourceExhaustedError("Azure list XML too large");
  std::unique_ptr<xmlDoc, decltype(&xmlFreeDoc)> doc(
      xmlReadMemory(body.data(), static_cast<int>(body.size()), nullptr,
                    "UTF-8",
                    XML_PARSE_NONET | XML_PARSE_NOERROR | XML_PARSE_NOWARNING),
      xmlFreeDoc);
  auto root = doc ? xmlDocGetRootElement(doc.get()) : nullptr;
  if (!IsElement(root, "EnumerationResults") || doc->intSubset ||
      doc->extSubset)
    return absl::DataLossError("invalid Azure EnumerationResults");
  auto blobs = Child(root, "Blobs");
  if (!blobs.ok()) return blobs.status();
  AzureBlobListPage page;
  for (auto blob = (*blobs)->children; blob; blob = blob->next) {
    if (blob->type != XML_ELEMENT_NODE) continue;
    if (!IsElement(blob, "Blob") || page.keys_.size() == max_keys)
      return absl::DataLossError("unexpected Azure list entry");
    auto name = Child(blob, "Name");
    if (!name.ok()) return name.status();
    auto key = FieldText(*name);
    if (!key.ok()) return key.status();
    if (key->empty()) return absl::DataLossError("empty Azure blob name");
    // Azure escapes individual names only when XML cannot represent them.
    std::unique_ptr<xmlChar, xmlFreeFunc> encoded(
        xmlGetProp(*name, BAD_CAST "Encoded"), xmlFree);
    if (xmlStrEqual(encoded.get(), BAD_CAST "true")) {
      key = DecodeKey(*key);
      if (!key.ok()) return key.status();
    } else if (encoded && !xmlStrEqual(encoded.get(), BAD_CAST "false")) {
      return absl::DataLossError("invalid Azure blob name encoding");
    }
    page.keys_.push_back(*std::move(key));
  }
  auto marker = Child(root, "NextMarker", false);
  if (!marker.ok()) return marker.status();
  if (*marker) {
    auto value = FieldText(*marker);
    if (!value.ok()) return value.status();
    if (!value->empty() && *value == previous_marker)
      return absl::DataLossError("repeated Azure list marker");
    page.next_token_ = *std::move(value);
  }
  return page;
}

absl::StatusOr<AzureBlobClient> AzureBlobClient::Create(
    net::HttpEndpoint endpoint, std::string account, std::string container,
    std::string_view base64_key, AzureAccountAddressing addressing,
    net::HttpRequestOptions options) {
  if (account.empty() ||
      !std::ranges::all_of(account,
                           [](unsigned char c) {
                             return absl::ascii_islower(c) ||
                                    absl::ascii_isdigit(c);
                           }) ||
      container.empty() || container.contains('/'))
    return absl::InvalidArgumentError("invalid Azure account or container");
  std::string key;
  if (!absl::Base64Unescape(base64_key, &key) || key.empty())
    return absl::InvalidArgumentError("invalid Azure storage account key");
  std::string path;
  if (addressing == AzureAccountAddressing::kPath)
    absl::StrAppend(&path, "/", account);
  absl::StrAppend(&path, "/", internal::Encode(container));
  return AzureBlobClient(std::move(endpoint), std::move(account),
                         std::move(path), std::move(key), options);
}

AzureBlobClient::AzureBlobClient(net::HttpEndpoint endpoint,
                                 std::string account, std::string path,
                                 std::string key,
                                 net::HttpRequestOptions options)
    : http_(std::move(endpoint)),
      account_(std::move(account)),
      container_path_(std::move(path)),
      key_(std::move(key)),
      options_(options) {
  options_.skip_error_body_ = true;
}

bycorf::Task<absl::StatusOr<HttpResponse>> AzureBlobClient::Send(
    HttpRequest request, unsigned expected,
    std::map<std::string, std::string> query) const {
  if (query.empty()) {
    if (request.target_.empty())
      co_return absl::InvalidArgumentError("empty Azure blob name");
    request.target_ = absl::StrCat(container_path_, "/",
                                   internal::Encode(request.target_, true));
  } else {
    request.target_ = container_path_;
  }
  auto status =
      internal::SignAzureRequest(request, query, account_, key_, absl::Now());
  if (!status.ok()) co_return status;
  auto response = co_await http_.Send(std::move(request), options_);
  if (!response.ok()) co_return response.status();
  status = internal::CheckResponse("Azure Blob", response->status_, expected);
  if (!status.ok()) co_return status;
  co_return std::move(response);
}

bycorf::Task<absl::StatusOr<std::string>> AzureBlobClient::Put(
    std::string key, std::string_view data, std::string if_match) const {
  HttpRequest request{
      .method_ = HttpMethod::kPut, .target_ = std::move(key), .body_ = data};
  if (!if_match.empty())
    request.headers_.push_back({"if-match", std::move(if_match)});
  auto response = co_await Send(std::move(request), 201);
  if (!response.ok()) co_return response.status();
  auto tag = response->Header("ETag");
  if (!tag || tag->empty())
    co_return absl::DataLossError("Azure PUT omitted ETag");
  co_return std::string(*tag);
}

bycorf::Task<absl::StatusOr<std::string>> AzureBlobClient::Get(
    std::string key) const {
  HttpRequest request{.method_ = HttpMethod::kGet, .target_ = std::move(key)};
  auto response = co_await Send(std::move(request), 200);
  if (!response.ok()) co_return response.status();
  co_return std::move(response->body_);
}

bycorf::Task<absl::Status> AzureBlobClient::Delete(std::string key) const {
  HttpRequest request{.method_ = HttpMethod::kDelete,
                      .target_ = std::move(key)};
  auto response = co_await Send(std::move(request), 202);
  co_return response.status();
}

bycorf::Task<absl::StatusOr<AzureBlobListPage>> AzureBlobClient::List(
    std::string prefix, std::string token, unsigned max_keys) const {
  if (!max_keys || max_keys > 5000)
    co_return absl::InvalidArgumentError("max_keys must be 1..5000");
  std::map<std::string, std::string> query{
      {"comp", "list"},
      {"restype", "container"},
      {"maxresults", absl::StrCat(max_keys)}};
  if (!prefix.empty()) query.emplace("prefix", std::move(prefix));
  if (!token.empty()) query.emplace("marker", token);
  HttpRequest request;
  auto response = co_await Send(std::move(request), 200, std::move(query));
  if (!response.ok()) co_return response.status();
  co_return internal::ParseAzureListPage(response->body_, token, max_keys);
}
}  // namespace lavik::object_store
