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

# Azure Blob client

`lavik::azure_blob_client` provides block blob PUT, GET, DELETE and flat
prefix listing within one container. The caller supplies a resolved endpoint,
a storage account and its Shared Key. The client signs each request and sends
it through the [outbound HTTP client](13-outbound-http.md) on the calling
Bycorf worker. Host-style endpoints address the container at `/container`.
Path-style endpoints such as Azurite address it at `/account/container`.
The signed resource includes the account name followed by that exact wire path.

PUT returns the service ETag. Passing it back in `If-Match` allows a caller
to replace the blob only while that ETag is current. A stale ETag returns
`FailedPrecondition`. If the connection fails before the final response
headers arrive, the caller owns reconciliation of the write outcome.

List returns one page of blob names and the service's opaque marker. The
caller passes the marker back with the same prefix until it receives an empty
marker. Page length alone cannot establish that enumeration is complete.
The [public API](../../include/lavik/object_store/azure_blob_client.h) is
independent of the storage engine and local device layout.
