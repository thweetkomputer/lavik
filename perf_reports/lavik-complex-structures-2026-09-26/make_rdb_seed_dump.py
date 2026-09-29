#!/usr/bin/env python3
# Copyright (C) 2026 EloqData Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Build one deterministic large Hash/Set DUMP for the benchmark seed.

Redis 8.8 writes an RDB v14 footer. These ordinary Set/Hash object encodings
are also understood by Lavik's v11 reader, so rewrite only the version and
CRC64 after checking the object type and Redis's original checksum. The
benchmark validates every imported key's cardinality and one sample value.
"""

import argparse
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import tempfile
import time

from run import read, resp, value


MASK = (1 << 64) - 1
POLYNOMIAL = 0xad93d23594c935a9
LAVIK_RDB_VERSION = 11


def crc64(data):
    """Redis CRC64, matching src/redis/rdb.cpp's reflected result."""
    table = []
    for byte in range(256):
        crc = byte << 56
        for _ in range(8):
            crc = ((crc << 1) & MASK) ^ (POLYNOMIAL if crc >> 63 else 0)
        table.append(crc)
    reversed_byte = bytes(int(f"{byte:08b}"[::-1], 2) for byte in range(256))
    crc = 0
    for byte in data:
        crc = ((crc << 8) & MASK) ^ table[(crc >> 56) ^ reversed_byte[byte]]
    return int(f"{crc:064b}"[::-1], 2)


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def make_dump(redis_binary, kind, field_bytes, entries):
    with tempfile.TemporaryDirectory(prefix="lavik-rdb-seed-") as temp:
        port = free_port()
        log = (Path(temp) / "redis.log").open("w")
        process = subprocess.Popen(
            [str(redis_binary), "--bind", "127.0.0.1", "--port", str(port),
             "--save", "", "--appendonly", "no", "--dir", temp],
            stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 20
            while True:
                if process.poll() is not None:
                    raise RuntimeError(f"Redis exited: {Path(temp, 'redis.log').read_text()}")
                try:
                    sock = socket.create_connection(("127.0.0.1", port), timeout=1)
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise TimeoutError("seed Redis startup")
                    time.sleep(0.05)
            with sock:
                sock.settimeout(600)
                stream = sock.makefile("rb")
                for first in range(0, entries, 1024):
                    end = min(first + 1024, entries)
                    if kind == "set":
                        arguments = ("SADD", "seed", *(value(i, field_bytes)
                                                      for i in range(first, end)))
                    else:
                        arguments = ("HSET", "seed", *(argument
                            for i in range(first, end)
                            for argument in (f"f{i:08d}", value(i, field_bytes))))
                    sock.sendall(resp(*arguments))
                    if read(stream) != end - first:
                        raise RuntimeError(f"seed insertion failed at {first}")
                sock.sendall(resp("SCARD" if kind == "set" else "HLEN", "seed"))
                if read(stream) != entries:
                    raise RuntimeError("seed cardinality mismatch")
                mid = entries // 2
                if kind == "set":
                    sock.sendall(resp("SISMEMBER", "seed", value(mid, field_bytes)))
                    valid = read(stream) == 1
                else:
                    sock.sendall(resp("HGET", "seed", f"f{mid:08d}"))
                    valid = read(stream) == value(mid, field_bytes)
                if not valid:
                    raise RuntimeError("seed sample mismatch")
                sock.sendall(resp("DUMP", "seed"))
                payload = read(stream)
                if not isinstance(payload, bytes):
                    raise RuntimeError("Redis returned no DUMP payload")
                return bytearray(payload)
        finally:
            process.terminate()
            process.wait(timeout=20)
            log.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=("hash", "set"))
    parser.add_argument("logical_bytes", type=int)
    parser.add_argument("field_bytes", type=int, choices=(128, 1024))
    parser.add_argument("output", type=Path)
    parser.add_argument("--redis-binary", type=Path, required=True)
    options = parser.parse_args()
    if (options.logical_bytes <= 0 or
            options.logical_bytes % options.field_bytes):
        parser.error("logical bytes must be a positive multiple of field bytes")
    entries = options.logical_bytes // options.field_bytes
    payload = make_dump(options.redis_binary, options.kind,
                        options.field_bytes, entries)
    expected_type = 2 if options.kind == "set" else 4
    if payload[0] != expected_type:
        raise RuntimeError(f"unexpected RDB object type {payload[0]}")
    original_version = int.from_bytes(payload[-10:-8], "little")
    expected_crc = int.from_bytes(payload[-8:], "little")
    if crc64(memoryview(payload)[:-8]) != expected_crc:
        raise RuntimeError("Redis DUMP checksum mismatch")
    if original_version > LAVIK_RDB_VERSION:
        payload[-10:-8] = LAVIK_RDB_VERSION.to_bytes(2, "little")
        payload[-8:] = crc64(memoryview(payload)[:-8]).to_bytes(8, "little")
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_bytes(payload)
    metadata = {
        "kind": options.kind, "logical_bytes": options.logical_bytes,
        "field_bytes": options.field_bytes, "entries": entries,
        "redis_binary": str(options.redis_binary),
        "redis_sha256": hashlib.sha256(options.redis_binary.read_bytes()).hexdigest(),
        "redis_dump_version": original_version,
        "output_dump_version": int.from_bytes(payload[-10:-8], "little"),
        "output_dump_bytes": len(payload),
        "output_sha256": hashlib.sha256(payload).hexdigest(),
    }
    options.output.with_suffix(".json").write_text(
        json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
