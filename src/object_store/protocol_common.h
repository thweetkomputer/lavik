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

#include <libxml/tree.h>

#include <string>
#include <string_view>

#include "absl/status/statusor.h"

namespace lavik::object_store::internal {

std::string Encode(std::string_view value, bool keep_slashes = false);
absl::StatusOr<std::string> DecodeKey(std::string_view encoded);
absl::Status CheckResponse(std::string_view provider, unsigned status,
                           unsigned expected);

// Look up a unique child and read scalar text without traversing entity
// references or nested elements. An absent optional child returns nullptr.
bool IsElement(xmlNodePtr node, const char* name);
absl::StatusOr<xmlNodePtr> Child(xmlNodePtr parent, const char* name,
                                 bool required = true);
absl::StatusOr<std::string> FieldText(xmlNodePtr field);

}  // namespace lavik::object_store::internal
