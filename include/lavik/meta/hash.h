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

// Durable intent and population-manifest fingerprints. OpenSSL owns the
// SHA-256 implementation; control framing and FDS do not use content hashes.

#include <openssl/sha.h>

#include <cstdlib>
#include <string_view>

#include "lavik/meta/commands.h"

namespace lavik::meta {

// Computes the stable SHA-256 representation used by existing durable data.
// Crypto-provider failure is fatal: returning a fabricated digest could alias
// different durable intents or population documents.
inline MetaHash256 MetaSha256(std::string_view data) {
  MetaHash256 digest{};
  if (SHA256(reinterpret_cast<const unsigned char*>(data.data()), data.size(),
             digest.data()) == nullptr) {
    std::abort();
  }
  return digest;
}

}  // namespace lavik::meta
