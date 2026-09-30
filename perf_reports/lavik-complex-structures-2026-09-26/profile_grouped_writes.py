#!/usr/bin/env python3
"""Run clean benchmark points, then separate 30-second grouped-write profiles.

Uses run.py's options and validation. At 1,280 and 5,120 connections, sample
20 seconds of each diagnostic run at 99 Hz with DWARF call stacks. Diagnostic
results live in subdirectories so they never enter the clean chart grid.
"""

import sys
import subprocess
import time
import os
from pathlib import Path
import run

original = run.measure


def option(name):
    for i, arg in enumerate(sys.argv):
        if arg.startswith(name + "="):
            return arg.split("=", 1)[1]
        if arg == name:
            return sys.argv[i + 1]
    raise ValueError(name)


def measure(directory, kind, size, field, entries, keys, op, conns, seconds, threads):
    original(directory, kind, size, field, entries, keys, op, conns, seconds, threads)
    if op != run.OPS[kind][1] or conns != 5120:
        return
    binary = option("--binary")
    pids = []
    for p in Path("/proc").iterdir():
        if not p.name.isdigit():
            continue
        try:
            args = (p / "cmdline").read_bytes().split(b"\0")
        except (OSError, PermissionError):
            continue
        if args[0] == os.fsencode(binary):
            pids.append(int(p.name))
    assert len(pids) == 1, pids
    for level in [1280, 5120]:
        d = directory / f"diagnostic-c{level}"
        d.mkdir(exist_ok=True)
        args = [
            "perf",
            "record",
            "-e",
            "task-clock",
            "-F",
            "99",
            "-g",
            "--call-graph",
            "dwarf,16384",
            "-p",
            str(pids[0]),
            "-o",
            str(d / "cpu.perf"),
            "--",
            "sleep",
            "20",
        ]
        run.save(
            d / "profile-provenance.json",
            {
                "source_commit": option("--source-commit"),
                "binary": binary,
                "pid": pids[0],
                "argv": args,
                "time": time.time(),
                "condition": {
                    "type": kind,
                    "bytes_per_key": size,
                    "field_bytes": field,
                    "keys": keys,
                    "connections": level,
                },
            },
        )
        with (d / "perf.log").open("w") as log:
            proc = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT)
            try:
                original(
                    d, kind, size, field, entries, keys, op, level, 30, min(16, level)
                )
            finally:
                rc = proc.wait(timeout=40)
            assert rc == 0, rc
        for name, mode in [("self", "--no-children"), ("inclusive", "--children")]:
            with (d / (name + ".txt")).open("w") as out:
                subprocess.run(
                    [
                        "perf",
                        "report",
                        "--stdio",
                        "--no-inline",
                        mode,
                        "--call-graph",
                        "none",
                        "--percent-limit",
                        "0.1",
                        "--sort",
                        "symbol",
                        "-i",
                        str(d / "cpu.perf"),
                    ],
                    stdout=out,
                    check=True,
                )


if __name__ == "__main__":
    run.measure = measure
    run.main()
