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

#include "protocol_common.h"

#include <charconv>

#include "absl/strings/ascii.h"
#include "absl/strings/str_cat.h"

namespace lavik::object_store::internal {
constexpr char kHex[] = "0123456789ABCDEF";

std::string Encode(std::string_view value, bool keep_slashes) {
  std::string encoded;
  for (unsigned char c : value) {
    if (absl::ascii_isalnum(c) || c == '-' || c == '_' || c == '.' ||
        c == '~' || (keep_slashes && c == '/')) {
      encoded += static_cast<char>(c);
    } else {
      encoded += '%';
      encoded += kHex[c >> 4];
      encoded += kHex[c & 15];
    }
  }
  return encoded;
}

// '+' is a literal byte in URI encoding.
absl::StatusOr<std::string> DecodeKey(std::string_view encoded) {
  std::string key;
  for (size_t i = 0; i < encoded.size(); ++i) {
    if (encoded[i] != '%') {
      key += encoded[i];
      continue;
    }
    if (encoded.size() - i < 3)
      return absl::DataLossError("truncated URL-encoded key");
    const char* digits = encoded.data() + i + 1;
    unsigned char byte;
    auto [end, ec] = std::from_chars(digits, digits + 2, byte, 16);
    if (ec != std::errc{} || end != digits + 2)
      return absl::DataLossError("invalid URL-encoded key");
    key += static_cast<char>(byte);
    i += 2;
  }
  return key;
}

absl::Status CheckResponse(std::string_view provider, unsigned status,
                           unsigned expected) {
  if (status == expected) return absl::OkStatus();
  const auto message = absl::StrCat(provider, " returned HTTP ", status);
  switch (status) {
    case 400:
      return absl::InvalidArgumentError(message);
    case 401:
    case 403:
      return absl::PermissionDeniedError(message);
    case 404:
      return absl::NotFoundError(message);
    case 409:
      return absl::AbortedError(message);
    case 412:
      return absl::FailedPreconditionError(message);
    case 429:
      return absl::ResourceExhaustedError(message);
    default:
      return status >= 500 ? absl::UnavailableError(message)
                           : absl::UnknownError(message);
  }
}

bool IsElement(xmlNodePtr node, const char* name) {
  return node && node->type == XML_ELEMENT_NODE &&
         xmlStrEqual(node->name, BAD_CAST name);
}

absl::StatusOr<xmlNodePtr> Child(xmlNodePtr parent, const char* name,
                                 bool required) {
  xmlNodePtr match = nullptr;
  for (auto child = parent->children; child; child = child->next) {
    if (!IsElement(child, name)) continue;
    if (match)
      return absl::DataLossError(
          absl::StrCat("duplicate listing field ", name));
    match = child;
  }
  if (required && !match)
    return absl::DataLossError(absl::StrCat("missing listing field ", name));
  return match;
}

absl::StatusOr<std::string> FieldText(xmlNodePtr field) {
  std::string value;
  for (auto part = field->children; part; part = part->next) {
    if (part->type == XML_COMMENT_NODE) continue;
    if (part->type != XML_TEXT_NODE && part->type != XML_CDATA_SECTION_NODE)
      return absl::DataLossError("invalid listing field");
    value += reinterpret_cast<const char*>(part->content);
  }
  return value;
}
}  // namespace lavik::object_store::internal
