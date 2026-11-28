/*
 * Copyright (C) 2026 EloqData Inc.
 * SPDX-License-Identifier: Apache-2.0
 */

#include "../storage/engine/impl.h"
#include "lavik/object_store/record_block_objects.h"

namespace lavik::object_store {

absl::Status RecordBlockImage::Install(const std::string& device,
                                       std::uint32_t local_slot) const {
  using namespace storage;
  if (bycorf::ThisWorker().self_)
    return absl::FailedPreconditionError(
        "install requires an offline provisioning thread");
  BlockHeader header;
  if (!DecodeBlockHeader(header_, &header) ||
      header.kind_ != BlockKind::kRecords ||
      header.committed_bytes_ != kBlockHeaderBytes + records_.size())
    return absl::FailedPreconditionError("incomplete record block image");

  auto geometry = ProbeBlockDevice(device);
  if (!geometry.ok()) return geometry.status();
  std::array<std::byte, kDirectIoAlignment> page;
  auto status = ReadExactlyAt(device, page, kDeviceLabelOffset);
  if (!status.ok()) return status;
  DeviceLabel label;
  if (!DecodeDeviceLabel(page, &label) ||
      label.version_ != kStorageFormatVersion ||
      label.capacity_blocks_ > geometry->size_bytes_ / kStorageBlockBytes ||
      local_slot < DataBlockBegin(label.capacity_blocks_) ||
      local_slot >= label.capacity_blocks_)
    return absl::InvalidArgumentError(
        "target must be a data slot on a formatted device");
  if (!RecordLocation::CanEncodeBlockIdentity(
          MakeBlockId(label.device_id_, local_slot), header.allocation_epoch_))
    return absl::OutOfRangeError(
        "target block identity exceeds the recovery index range");
  const auto base = LocalBlockOffset(local_slot);
  const auto byte = local_slot / 8;
  const auto index = byte / kMetadataPagePayloadBytes;
  const auto bytes = std::min(kMetadataPagePayloadBytes,
                              ScanBitmapBytes(label.capacity_blocks_) -
                                  index * kMetadataPagePayloadBytes);
  auto bitmap =
      ReadMetadataPagePair(device, kScanBitmapMetadataOffset,
                           MetadataPageKind::kScanBitmap, index, bytes);
  if (!bitmap.ok()) return bitmap.status();
  auto& entry = bitmap->payload_[byte % kMetadataPagePayloadBytes];
  const auto bit = static_cast<std::byte>(1u << (local_slot % 8));
  const bool active = (entry & bit) != std::byte{0};
  std::array<std::byte, kBlockHeaderBytes> slots{};
  if (active) {
    status = ReadExactlyAt(device, slots, base);
    if (!status.ok()) return status;
    if (DecodeBlockHeaderPages(slots, nullptr))
      return absl::AlreadyExistsError("target record block slot is occupied");
  }
  // A clear scan bit authoritatively frees a slot even if a previous
  // allocation left a valid, newer header on disk. Clear both copies durably
  // before activation. An active slot with a torn first header can be retried.
  if (!active || !IsZero(slots)) {
    slots.fill(std::byte{0});
    status = WriteExactlyAt(device, slots, base, true);
    if (!status.ok()) return status;
  }
  if (!active) {
    entry |= bit;
    if (bitmap->state_.generation_ == std::numeric_limits<std::uint64_t>::max())
      return absl::OutOfRangeError("scan bitmap generation exhausted");
    EncodeMetadataPage(MetadataPageKind::kScanBitmap, index,
                       bitmap->state_.generation_ + 1, bitmap->payload_, page);
    status =
        WriteExactlyAt(device, page,
                       MetadataPageSlotOffset(kScanBitmapMetadataOffset, index,
                                              1 - bitmap->state_.active_slot_),
                       true);
    if (!status.ok()) return status;
  }

  status = WriteExactlyAt(device, std::as_bytes(std::span(records_)),
                          base + kBlockHeaderBytes, true);
  if (!status.ok()) return status;
  return WriteExactlyAt(
      device, header_,
      base + HeaderSlot(header.header_sequence_) * kBlockHeaderSlotBytes, true);
}
}  // namespace lavik::object_store
