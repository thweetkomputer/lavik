#!/usr/bin/env python3
# Copyright (C) 2026 EloqData Inc.
# SPDX-License-Identifier: Apache-2.0
"""Exercise the Bycorf probe against disposable loopback object services."""

import argparse
import base64
import os
import secrets
import subprocess
import tempfile
import time
from contextlib import ExitStack, contextmanager
from http.client import HTTPConnection, HTTPException
from pathlib import Path

import boto3
from azure.storage.blob import BlobServiceClient
from botocore.config import Config


@contextmanager
def service(image, port, credentials, ready_path, ready_statuses, *command):
    # Only the ID returned for this run may be removed. Docker chooses a free
    # loopback port and --rm discards the anonymous data volume on shutdown.
    args = ["docker", "run", "--rm", "-d", "-p", f"127.0.0.1::{port}"]
    for name in credentials:
        args.extend(["-e", name])
    ident = subprocess.check_output(
        [*args, image, *command], env=os.environ | credentials, text=True
    ).strip()
    try:
        binding = subprocess.check_output(
            ["docker", "port", ident, f"{port}/tcp"], text=True
        ).strip()
        local_port = int(binding.rsplit(":", 1)[1])
        deadline = time.monotonic() + 30
        while True:
            connection = HTTPConnection("127.0.0.1", local_port, timeout=1)
            try:
                connection.request("GET", ready_path)
                if connection.getresponse().status in ready_statuses:
                    break
            except (OSError, HTTPException):
                pass
            finally:
                connection.close()
            if time.monotonic() >= deadline:
                raise TimeoutError(f"{image} did not become ready")
            time.sleep(0.1)
        yield local_port
    finally:
        subprocess.run(
            ["docker", "rm", "-f", ident], check=True, stdout=subprocess.DEVNULL
        )


@contextmanager
def raw_test_devices():
    # Use fresh loop devices for every run. A private node avoids changing the
    # permissions on a shared /dev/loopN, even while another test is running.
    with tempfile.TemporaryDirectory() as directory, ExitStack() as cleanup:
        nodes = []
        privileged = [] if os.geteuid() == 0 else ["sudo", "-n"]
        for name in ("source", "target"):
            image = Path(directory) / f"{name}.img"
            with image.open("xb") as f:
                f.truncate(128 * 1024 * 1024)
            loop = subprocess.check_output(
                [*privileged, "losetup", "--find", "--show", image], text=True
            ).strip()
            cleanup.callback(
                subprocess.run, [*privileged, "losetup", "-d", loop], check=True
            )
            device = os.stat(loop).st_rdev
            node = Path(directory) / name
            subprocess.run(
                [
                    *privileged,
                    "mknod",
                    "-m",
                    "666",
                    node,
                    "b",
                    str(os.major(device)),
                    str(os.minor(device)),
                ],
                check=True,
            )
            nodes.append(node)
        yield nodes


def run_probe(binary, provider, port, container, account, secret, raw_blocks):
    with ExitStack() as cleanup:
        devices = cleanup.enter_context(raw_test_devices()) if raw_blocks else []
        subprocess.run(
            [binary, provider, str(port), *devices],
            input=f"{container}\n{account}\n{secret}\n",
            text=True,
            check=True,
            timeout=60 if raw_blocks else 45,
        )
    if raw_blocks:
        print(
            f"{provider}: three flushes, gap and CRC checks, relocated raw-device cold recovery passed",
            flush=True,
        )
    else:
        print(
            f"{provider}: signed binary PUT/GET, conditional overwrite, paginated prefix list, signature rejection and DELETE passed",
            flush=True,
        )


def rustfs(binary, raw_blocks):
    key = secrets.token_hex(12).upper()
    secret = secrets.token_hex(24)
    with service(
        "rustfs/rustfs:1.0.0",
        9000,
        {"RUSTFS_ACCESS_KEY": key, "RUSTFS_SECRET_KEY": secret},
        "/health/ready",
        {200},
        "/data",
    ) as port:
        client = boto3.client(
            "s3",
            endpoint_url=f"http://127.0.0.1:{port}",
            region_name="us-east-1",
            aws_access_key_id=key,
            aws_secret_access_key=secret,
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
                proxies={},
                connect_timeout=2,
                read_timeout=5,
            ),
        )
        bucket = "lavik-probe"
        client.create_bucket(Bucket=bucket)
        run_probe(binary, "s3", port, bucket, key, secret, raw_blocks)


def azurite(binary, raw_blocks):
    account = "lavikprobe"
    key = base64.b64encode(secrets.token_bytes(32)).decode()
    with service(
        "mcr.microsoft.com/azure-storage/azurite:3.35.0",
        10000,
        {"AZURITE_ACCOUNTS": f"{account}:{key}"},
        "/lavikprobe/probe/uncreated",
        {403, 404},
        "azurite-blob",
        "--blobHost",
        "0.0.0.0",
    ) as port:
        client = BlobServiceClient(
            f"http://127.0.0.1:{port}/{account}",
            credential=key,
            api_version="2023-11-03",
            use_env_settings=False,
        )
        container = client.create_container("lavik-probe")
        run_probe(
            binary, "azure", port, container.container_name, account, key, raw_blocks
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "binary", help="path to the object client or record block probe"
    )
    parser.add_argument("--provider", choices=("s3", "azure", "both"), default="both")
    parser.add_argument(
        "--raw-blocks",
        action="store_true",
        help="run lavik_record_block_probe on two new loop devices",
    )
    args = parser.parse_args()
    if args.provider in ("s3", "both"):
        rustfs(args.binary, args.raw_blocks)
    if args.provider in ("azure", "both"):
        azurite(args.binary, args.raw_blocks)
