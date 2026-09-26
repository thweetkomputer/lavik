#!/usr/bin/env python3
"""Prepare and restore only this host's six dedicated benchmark NVMe devices.

Run as root. The prepare command discards their prior scratch dataset before
binding the controllers to VFIO; it never selects the OS or workspace NVMe.
"""

import argparse
import json
import os
from pathlib import Path
import subprocess
import time


ROOT = Path(__file__).resolve().parent
SETUP = Path("/mnt/dev/lavik-main-repro-20260925/bycorf/third_party/spdk/scripts/setup.sh")
SERIAL_PCI = {
    "9971393486cee1f00001": "3d64:00:00.0",
    "9971393486cee1f00002": "e440:00:00.0",
    "9971393486cee1f00003": "c30a:00:00.0",
    "9971393486cee1f00004": "825f:00:00.0",
    "9971393486cee1f00005": "e051:00:00.0",
    "9971393486cee1f00006": "7292:00:00.0",
}
PCI_ALLOWED = " ".join(SERIAL_PCI.values())
HUGEPAGES = Path("/sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages")
UNSAFE = Path("/sys/module/vfio/parameters/enable_unsafe_noiommu_mode")


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def run(*args, env=None):
    completed = subprocess.run(args, text=True, capture_output=True, env=env)
    with (ROOT / "spdk-host-commands.jsonl").open("a") as output:
        output.write(json.dumps({"time": time.time(), "argv": args,
                                 "exit_code": completed.returncode,
                                 "stdout": completed.stdout,
                                 "stderr": completed.stderr}) + "\n")
    completed.check_returncode()


def checked_kernel_devices():
    devices = {}
    for controller in Path("/sys/class/nvme").glob("nvme*"):
        serial = (controller / "serial").read_text().strip()
        if serial not in SERIAL_PCI:
            continue
        bdf = (controller / "device").resolve().name
        assert bdf == SERIAL_PCI[serial], (serial, bdf)
        device = Path("/dev") / (controller.name + "n1")
        block = Path("/sys/class/block") / device.name
        assert device.exists() and block.exists(), device
        assert not list((block / "holders").iterdir()), device
        assert subprocess.run(["findmnt", "-rn", "-S", str(device)],
                              capture_output=True).returncode == 1, device
        assert subprocess.run(["fuser", str(device)],
                              capture_output=True).returncode == 1, device
        devices[serial] = str(device)
    assert set(devices) == set(SERIAL_PCI), devices
    return devices


def no_servers():
    for name in ("lavik", "redis-server", "valkey-server", "asd"):
        assert subprocess.run(["pgrep", "-x", name],
                              capture_output=True).returncode == 1, name


def setup(action):
    env = dict(os.environ, PCI_ALLOWED=PCI_ALLOWED, DRIVER_OVERRIDE="vfio-pci",
               HUGEMEM="8192")
    run(str(SETUP), action, env=env)


def assert_driver(driver):
    for bdf in SERIAL_PCI.values():
        actual = Path("/sys/bus/pci/devices", bdf, "driver").resolve().name
        assert actual == driver, (bdf, actual)


def prepare():
    assert not (ROOT / "spdk-ready.json").exists()
    no_servers()
    devices = checked_kernel_devices()
    assert_driver("nvme")
    run("modprobe", "vfio-pci")
    original = {"time": time.time(), "hugepages": HUGEPAGES.read_text().strip(),
                "unsafe_noiommu": UNSAFE.read_text().strip(),
                "devices": devices, "pci_allowed": PCI_ALLOWED}
    save(ROOT / "spdk-host-original.json", original)
    for serial in sorted(devices):
        print("discard", serial, devices[serial], flush=True)
        run("blkdiscard", devices[serial])
    if not list(Path("/sys/kernel/iommu_groups").iterdir()):
        UNSAFE.write_text("1\n")
    setup("config")
    assert_driver("vfio-pci")
    save(ROOT / "spdk-ready.json", {"time": time.time(), "pci_allowed": PCI_ALLOWED})


def restore():
    assert (ROOT / "spdk-ready.json").exists()
    no_servers()
    assert_driver("vfio-pci")
    setup("reset")
    run("udevadm", "settle")
    assert_driver("nvme")
    original = json.loads((ROOT / "spdk-host-original.json").read_text())
    HUGEPAGES.write_text(original["hugepages"] + "\n")
    UNSAFE.write_text(("1" if original["unsafe_noiommu"] == "Y" else "0") + "\n")
    save(ROOT / "spdk-restored.json", {"time": time.time(), "devices": checked_kernel_devices(),
                                       "hugepages": HUGEPAGES.read_text().strip(),
                                       "unsafe_noiommu": UNSAFE.read_text().strip()})


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
