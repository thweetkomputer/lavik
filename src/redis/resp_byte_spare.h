/*
 * Copyright (C) 2026 EloqData Inc.
 * SPDX-License-Identifier: Apache-2.0
 */

#pragma once

#include <utility>

#include "lavik/command_args.h"
#include "lavik/memory.h"

namespace lavik {

// Only the embedded request slot is recycled. Independently owned pipeline or
// MULTI requests can outlive the connection and never reference its spare.
class alignas(64) RespByteSpare final : public CommandByteSpare {
 public:
  void TryGrow(Bytes& bytes, std::size_t additional) noexcept override {
    if (spare_.capacity() <= CommandArgs::kInlineBytes ||
        bytes.size() > spare_.capacity() ||
        additional > spare_.capacity() - bytes.size())
      return;
    // Copy the existing prefix before replacing its backing allocation. The
    // incoming payload is appended directly into the spare by the parser.
    spare_.assign(bytes.begin(), bytes.end());
    bytes.clear();
    bytes.swap(spare_);
  }

  void Offer(Bytes& bytes) noexcept override {
    constexpr std::size_t kMaxBytes = 4 * 1024;
    // Keep the larger eligible return so varying key lengths can hit the
    // same spare on subsequent requests.
    if (bytes.capacity() <= spare_.capacity() || bytes.capacity() > kMaxBytes)
      return;
    // Admit one worker cache budget per burst. Keeping the credit while the
    // vector is on loan avoids touching admission counters on every SET.
    if (credit_.bytes() == 0) {
      auto reservation = TryReserveMemory(kMaxBytes);
      if (!reservation) return;
      credit_.Adopt(&*reservation, kMaxBytes);
    }
    bytes.resize(0);  // Abseil clear() would free the backing allocation.
    spare_.swap(bytes);
    recently_returned_ = true;
  }

  // Called once per second by the owner. A full tick without a return
  // expires both idle storage and credit without reading a clock per request.
  void Tick() noexcept {
    if (!credit_.bytes()) return;
    if (!std::exchange(recently_returned_, false) ||
        WouldExceedMemoryLimit(0)) {
      spare_.clear();
      credit_.Reset();
    }
  }

 private:
  Bytes spare_;
  RetainedMemoryCharge credit_;
  bool recently_returned_ = false;
};

}  // namespace lavik
