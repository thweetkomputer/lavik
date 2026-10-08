#!/usr/bin/env python3
"""Stop a large benchmark fill before it exhausts host memory."""

import argparse
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


def available_kib():
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1])
    raise RuntimeError("MemAvailable is missing from /proc/meminfo")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--minimum-available-gib", type=float, default=20)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command or args.minimum_available_gib <= 0:
        parser.error("a command and positive memory floor are required")
    # The benchmark host has no swap. MemAvailable includes kernel reclaimable
    # cache, so it is a better stop condition than one server process's RSS.
    floor_kib = int(args.minimum_available_gib * 1024 * 1024)
    # Keep the runner, benchmark client, and database server in one process
    # group. A signal to the Python runner alone leaves fill worker threads
    # running while ThreadPoolExecutor waits for them to finish.
    process = subprocess.Popen(command, start_new_session=True)

    def stop_group(sig):
        try:
            os.killpg(process.pid, sig)
        except ProcessLookupError:
            pass

    stopped_for_memory = False
    try:
        while process.poll() is None:
            remaining = available_kib()
            if remaining < floor_kib:
                stopped_for_memory = True
                print(f"MemAvailable {remaining / 1024 / 1024:.1f} GiB fell below "
                      f"{args.minimum_available_gib:g} GiB; stopping benchmark",
                      file=sys.stderr, flush=True)
                stop_group(signal.SIGTERM)
                break
            time.sleep(1)
    except KeyboardInterrupt:
        stop_group(signal.SIGINT)
    try:
        code = process.wait(timeout=30)
    except subprocess.TimeoutExpired:
        stop_group(signal.SIGKILL)
        code = process.wait(timeout=10)
    return 99 if stopped_for_memory else code


if __name__ == "__main__":
    sys.exit(main())
