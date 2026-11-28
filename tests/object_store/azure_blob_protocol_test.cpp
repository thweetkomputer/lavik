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

#include "azure_blob_protocol.h"

#include "absl/strings/str_cat.h"
#include "gtest/gtest.h"

namespace lavik::object_store::internal {
namespace {

// Signatures from azure-storage-blob's SharedKeyCredentialPolicy, using the
// host-style service URL. The emulator round trip exercises path-style URLs.
absl::Time SigningTime() {
  return absl::FromCivil(absl::CivilSecond(2026, 1, 2, 3, 4, 5),
                         absl::UTCTimeZone());
}

TEST(AzureBlobProtocol, SignsConditionalAndEmptyWrites) {
  std::string bytes("new\0bytes", 9);
  net::HttpRequest request{.method_ = net::HttpMethod::kPut,
                           .target_ = "/container/name%20%25",
                           .headers_ = {{"if-match", "\"old\""}},
                           .body_ = bytes};
  ASSERT_TRUE(
      SignAzureRequest(request, {}, "acct", "fixture-key", SigningTime()).ok());
  EXPECT_EQ(request.headers_.back().value_,
            "SharedKey acct:r9GqB30EMzOIk+/zxmqQ4erCTC6a/VI5hGhgnZXCAeo=");
  net::HttpRequest empty{.method_ = net::HttpMethod::kPut,
                         .target_ = "/container/empty"};
  ASSERT_TRUE(
      SignAzureRequest(empty, {}, "acct", "fixture-key", SigningTime()).ok());
  EXPECT_EQ(empty.headers_.back().value_,
            "SharedKey acct:rcj/36wSFuTVQrrpbndjgc+Nqkve0ax+nXZdbyKtzCQ=");
}

TEST(AzureBlobProtocol, SignsDecodedQueryAndSendsEncodedMarker) {
  net::HttpRequest request{.target_ = "/container"};
  const auto status = SignAzureRequest(request,
                                       {{"restype", "container"},
                                        {"prefix", "p/"},
                                        {"maxresults", "1"},
                                        {"marker", "%+ &"},
                                        {"comp", "list"}},
                                       "acct", "fixture-key", SigningTime());
  ASSERT_TRUE(status.ok()) << status;
  EXPECT_EQ(request.target_,
            "/container?comp=list&marker=%25%2B%20%26&maxresults=1&prefix=p%2F&"
            "restype=container");
  EXPECT_EQ(request.headers_.back().value_,
            "SharedKey acct:NsDbaQwyYKrrM2nny5zYlEScskdWBklKiVonA2+303k=");
}

TEST(AzureBlobProtocol, DecodesOnlyNamesMarkedEncoded) {
  auto page = ParseAzureListPage(
      "<EnumerationResults><Blobs><Blob><Name>a+%2F&amp;</Name></Blob>"
      "<Blob><Name Encoded='true'>a%EF%BF%BE%25+</Name></Blob></Blobs>"
      "<NextMarker>%2F/+&amp;</NextMarker></EnumerationResults>",
      "", 2);
  ASSERT_TRUE(page.ok()) << page.status();
  EXPECT_EQ(page->keys_,
            (std::vector<std::string>{"a+%2F&", "a\xef\xbf\xbe%+"}));
  EXPECT_EQ(page->next_token_, "%2F/+&");
}

TEST(AzureBlobProtocol, ChecksPageStructureBeforeReturningKeys) {
  for (const auto* fields :
       {"<Blobs>", "<NextMarker/>", "<Blobs/><Blobs/>",
        "<Blobs><Blob/></Blobs>",
        "<Blobs><Blob><Name>a</Name><Name>b</Name></Blob></Blobs>",
        "<Blobs><Blob><Name Encoded='true'>%Q0</Name></Blob></Blobs>",
        "<Blobs><Blob><Name>a</Name></Blob><Blob><Name>b</Name></Blob></Blobs>",
        "<Blobs/><NextMarker>old</NextMarker>",
        "<Blobs/><NextMarker/><NextMarker/>"}) {
    auto page = ParseAzureListPage(
        absl::StrCat("<EnumerationResults>", fields, "</EnumerationResults>"),
        "old", 1);
    EXPECT_TRUE(absl::IsDataLoss(page.status())) << fields;
  }
  for (const auto* fields : {"<Blobs/>", "<Blobs/><NextMarker/>"}) {
    auto page = ParseAzureListPage(
        absl::StrCat("<EnumerationResults>", fields, "</EnumerationResults>"),
        "old", 1);
    ASSERT_TRUE(page.ok()) << page.status();
    EXPECT_TRUE(page->keys_.empty());
    EXPECT_TRUE(page->next_token_.empty());
  }
}

TEST(AzureBlobProtocol, RejectsInvalidCredentialsAtSetup) {
  for (auto* key : {"", "%%%?"})
    EXPECT_TRUE(absl::IsInvalidArgument(
        AzureBlobClient::Create({}, "acct", "container", key).status()));
}

}  // namespace
}  // namespace lavik::object_store::internal
