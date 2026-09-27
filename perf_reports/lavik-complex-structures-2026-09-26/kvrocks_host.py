#!/usr/bin/env python3
"""Mount a scratch RAID0 over the verified six benchmark NVMe devices."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time

import spdk_host

ROOT = Path(__file__).resolve().parent
MOUNT = Path("/mnt/lavik-complex-kvrocks-raid")
MD = Path("/dev/md127")
READY = ROOT / "kvrocks-raid-ready.json"


def run(*args):
    completed = subprocess.run(args, text=True, capture_output=True)
    with (ROOT / "kvrocks-host-commands.jsonl").open("a") as output:
        output.write(json.dumps({"time": time.time(), "argv": args,
                                 "exit_code": completed.returncode,
                                 "stdout": completed.stdout,
                                 "stderr": completed.stderr}) + "\n")
    completed.check_returncode()


def prepare():
    assert not READY.exists() and not (ROOT / "spdk-ready.json").exists()
    spdk_host.no_servers()
    devices = spdk_host.checked_kernel_devices()
    spdk_host.assert_driver("nvme")
    assert subprocess.run(["findmnt", "-rn", str(MOUNT)], capture_output=True).returncode == 1
    assert subprocess.run(["mdadm", "--detail", str(MD)], capture_output=True).returncode != 0
    MOUNT.mkdir(exist_ok=True)
    assert not any(MOUNT.iterdir()), MOUNT
    members = [devices[serial] for serial in sorted(devices)]
    for member in members:
        run("blkdiscard", member)
    raid_created = mounted = False
    try:
        run("mdadm", "--create", str(MD), "--run", "--level=0",
            f"--raid-devices={len(members)}", "--metadata=1.2", "--chunk=512",
            *members)
        raid_created = True
        run("mkfs.xfs", "-f", "-K", str(MD))
        run("mount", "-o", "noatime", str(MD), str(MOUNT))
        mounted = True
        assert subprocess.check_output(
            ["findmnt", "-n", "-o", "FSTYPE", "--target", str(MOUNT)],
            text=True).strip() == "xfs"
        run("mdadm", "--detail", str(MD))
        data = MOUNT / "data"
        data.mkdir()
        run("chown", "azureuser:azureuser", str(data))
        READY.write_text(json.dumps({"time": time.time(), "members": members,
                                     "mount": str(MOUNT), "md": str(MD)}, indent=2) + "\n")
    except Exception:
        if mounted:
            run("umount", str(MOUNT))
        if raid_created:
            run("mdadm", "--stop", str(MD))
            for member in members:
                run("mdadm", "--zero-superblock", member)
        raise


def restore():
    assert READY.exists()
    prepared = json.loads(READY.read_text())
    spdk_host.no_servers()
    # A device may remain briefly busy after mdadm stops. Keep the ready
    # marker until every verification succeeds, and let a retry finish an
    # already-unmounted cleanup without recreating or reformatting the array.
    mounted = subprocess.run(["findmnt", "-rn", str(MOUNT)],
                             capture_output=True).returncode == 0
    array_active = subprocess.run(["mdadm", "--detail", str(MD)],
                                  capture_output=True).returncode == 0
    if mounted:
        assert array_active
        run("umount", str(MOUNT))
    if array_active:
        run("mdadm", "--stop", str(MD))
    for member in prepared["members"]:
        if subprocess.run(["mdadm", "--examine", member],
                          capture_output=True).returncode == 0:
            run("mdadm", "--zero-superblock", member)
    run("udevadm", "settle")
    spdk_host.assert_driver("nvme")
    assert set(prepared["members"]) == set(spdk_host.checked_kernel_devices().values())
    (ROOT / "kvrocks-raid-restored.json").write_text(
        json.dumps({"time": time.time(), "prepared": prepared}, indent=2) + "\n")
    READY.unlink()


if __name__ == "__main__":
    assert os.geteuid() == 0
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "restore"))
    parser.add_argument("--discard-scratch", action="store_true")
    options = parser.parse_args()
    if options.action == "prepare":
        assert options.discard_scratch, "prepare requires --discard-scratch"
        prepare()
    else:
        restore()
