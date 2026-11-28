/*
 * Copyright (C) 2026 EloqData Inc.
 * SPDX-License-Identifier: Apache-2.0
 */

#include "lavik/object_store/azure_blob_client.h"
#include "lavik/object_store/s3_client.h"
#include "record_block_objects_impl.h"

namespace lavik::object_store {
template class RecordBlockObjects<S3Client>;
template class RecordBlockObjects<AzureBlobClient>;
}  // namespace lavik::object_store
