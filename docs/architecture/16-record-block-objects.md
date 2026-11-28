<!--
Copyright (C) 2026 EloqData Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
-->

# Ordinary block flush objects

A storage engine embedding can attach an asynchronous publisher to ordinary
record block flushes. The flusher lends it the encoded 4 KiB header slot and
the new aligned bytes after both local syncs, while staging remains pinned and
the store lock is released. Flush completion waits for the publisher. A
terminal error latches the writer's flush failure even though the local block
has already crossed its durability boundary.

`RecordBlockObjects` binds a caller-assigned remote ID to one source block
allocation. The owner reserves a fresh ID, routes that allocation's flushes
in order on one worker, and retains its objects through restore. The object
key is the decimal remote ID, an underscore and the decimal starting offset.
Its body is the encoded header slot followed by the data from that offset to
the header's committed boundary. The first data offset is 8192. Subsequent
offsets and header sequences advance contiguously. A timed-out PUT gets one
retry with the same key and bytes. A terminal request error stops the writer.

A reader enumerates a quiesced remote ID using either the [S3](14-s3-object-client.md)
or [Azure Blob](15-azure-blob-client.md) adapter. It checks offsets in numeric
order, each slot's CRC, sequence, allocation identity and data length, and
assembles at most one 8 MiB block. The header CRC covers the slot. Records
retain their original data-checksum policy. A gap before a listed fragment
invalidates the image. Determining whether a whole trailing flush or another
block is absent requires information outside that block's objects.

An offline provisioning thread installs the validated image into a free
data slot on an exclusively owned, freshly formatted raw device. It uses the
target label and scan bitmap, clears stale headers before slot activation,
syncs the data, and publishes the last encoded header in the slot selected by
its sequence. A cold start discovers the restored block through the ordinary
[recovery scan](04-storage-and-recovery.md#startup-and-recovery).

The [public API](../../include/lavik/object_store/record_block_objects.h) has
single-allocation scope. A database-wide restore must also coordinate epochs,
referenced blocks and transaction decisions across allocations.
