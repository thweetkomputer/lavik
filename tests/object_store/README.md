# Local object storage round trip

This test runs one Bycorf worker against RustFS (S3) and Azurite (Azure Blob).
The driver starts a disposable Docker container on a random loopback port
and creates the bucket or container. It passes fresh credentials over stdin to
the C++ [S3 client](../../include/lavik/object_store/s3_client.h) or
[Azure Blob client](../../include/lavik/object_store/azure_blob_client.h).
Each client signs its own requests over Lavik's
[HTTP client](../../include/lavik/net/http_client.h).

Both services exercise binary PUT/GET, ETag replacement and stale ETag
rejection, bounded downloads, deletion and missing keys. The probe lists
across a page boundary using a UTF-8 prefix with reserved characters, checks
that a key outside the prefix is excluded, and verifies that each service
rejects a request signed with the wrong key. The Azure probe uses host-style
and path-style requests against the same container.

Use a Linux host with io_uring, Docker access, the Lavik build prerequisites,
and Python 3.10 or newer.
From the repository root, with submodules initialized:

```sh
cmake -S . -B build -DBUILD_TESTING=ON
cmake --build build --target lavik_http_client_test lavik_s3_protocol_test lavik_azure_blob_protocol_test lavik_object_store_probe
ctest --test-dir build --output-on-failure -R '^lavik_(http_client|s3|azure_blob)_protocol$'
python3 -m venv /tmp/lavik-object-store-venv
/tmp/lavik-object-store-venv/bin/pip install boto3==1.44.7 azure-storage-blob==12.19.1
/tmp/lavik-object-store-venv/bin/python tests/object_store/roundtrip.py build/lavik_object_store_probe
```

The HTTP protocol test runs its delayed HTTPS peer on the same worker as the
client. The provider protocol tests check fixed signatures against their SDKs and
exercise malformed listings, key decoding and opaque markers. All protocol
tests run offline.

Pass `--provider s3` or `--provider azure` to run one service. Each run
generates its own credentials and removes its containers on exit.

## Restore a flushed block on raw devices

The record-block probe runs three real flushes of the same allocation. It
downloads the block, checks rejection of a bad header and a missing middle
fragment, installs the valid image at a different physical slot, and reads
all three records after a cold storage startup.

The driver allocates two disposable Linux loop devices per provider. Run it
on a host with Docker, loop device support, and root access for `losetup` and
`mknod` (via noninteractive sudo when running as a regular user). The
temporary directory must allow private device nodes.

```sh
cmake --build build --target lavik_record_block_objects_test lavik_record_block_probe
ctest --test-dir build -R '^lavik_record_block_objects$' --output-on-failure
/tmp/lavik-object-store-venv/bin/python tests/object_store/roundtrip.py --raw-blocks build/lavik_record_block_probe
```

The offline protocol test simulates a lost PUT acknowledgement and checks
retry bytes, allocation identity, and terminal failure.
