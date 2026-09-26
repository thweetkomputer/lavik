#!/usr/bin/env python3
"""Run the peer sweep against the allowlisted SPDK Lavik storage set."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time

import run as bench
import spdk_host


ROOT = Path(__file__).resolve().parent
DEFAULT_BINARY = Path("/mnt/dev/lavik/build/large-values-spdk/lavik")


def main():
    assert os.geteuid() == 0, "run as root for SPDK VFIO and memlock"
    parser = argparse.ArgumentParser()
    parser.add_argument("tag")
    parser.add_argument("--binary", type=Path, default=DEFAULT_BINARY)
    parser.add_argument("--source-tree", type=Path, default=ROOT.parents[1])
    parser.add_argument("--sizes", default=",".join(map(str, bench.SIZES)))
    parser.add_argument("--levels", default="80,320,640,1280")
    parser.add_argument("--seconds", type=int, default=15)
    parser.add_argument("--backlog-mb", type=int)
    parser.add_argument("--kinds", default="GET,SET")
    options = parser.parse_args()
    assert (ROOT / "spdk-ready.json").exists()
    spdk_host.assert_driver("vfio-pci")
    directory = ROOT / "raw" / ("lavik-" + options.tag)
    directory.mkdir(parents=True, exist_ok=True)
    levels = tuple(map(int, options.levels.split(",")))
    sizes = tuple(map(int, options.sizes.split(",")))
    assert all(c > 0 and c % 16 == 0 for c in levels)
    bdfs = list(spdk_host.SERIAL_PCI.values())
    binary = options.binary.resolve()
    source_tree = options.source_tree.resolve()
    command = ["prlimit", "--memlock=unlimited:unlimited", "--nofile=65535:65535",
               "taskset", "-c", "0-15", str(binary), "--network=kernel",
               "--storage=spdk", "--bind=" + bench.HOST, "--port=" + bench.PORT,
               "--metrics-port=0", "--threads=12", "--pin-workers",
               "--maxclients=10000", "--busy-poll-us=20",
               "--foreground-budget-us=1000", "--background-budget-us=10",
               "--background-warrant-percent=1", "--tomb-raider-interval-ms=0",
               "--spdk-max-completions-per-poll=16", "--spdk-foreground-pre-poll-us=5",
               "--defrag-paused", "--log-dir=" + str(directory / "logs")]
    command += ["--data-file=spdk://" + bdf + "/1" for bdf in bdfs]
    environment = dict(os.environ, BYCORF_EAL_ARGS=" ".join("-a " + bdf for bdf in bdfs),
                       BYCORF_DPDK_MEMORY_MB="8192")
    bench.save(directory / "server-command.json", command)
    bench.save(directory / "server-provenance.json",
               {"binary": str(binary), "sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
                "source_commit": subprocess.check_output(
                    ["git", "-C", str(source_tree), "rev-parse", "HEAD"],
                    text=True).strip(),
                "bycorf_commit": subprocess.check_output(
                    ["git", "-C", str(source_tree / "bycorf"),
                     "rev-parse", "HEAD"], text=True).strip(),
                "bdfs": bdfs})
    if bench.cli_available():
        raise RuntimeError("Benchmark port already occupied")
    with (directory / "server.log").open("w") as output:
        process = subprocess.Popen(command, stdout=output, stderr=subprocess.STDOUT,
                                   env=environment)
    try:
        for _ in range(6000):
            if process.poll() is not None:
                raise RuntimeError("Lavik exited during startup")
            if bench.cli_available():
                break
            time.sleep(0.2)
        else:
            raise TimeoutError("Lavik startup")
        print("Lavik started", process.pid, flush=True)
        if options.backlog_mb is not None:
            assert options.backlog_mb >= 8
            assert bench.cli("CONFIG", "SET", "tx-backlog-limit-mb-per-worker",
                             options.backlog_mb) == "OK"
        bench.save(directory / "startup.json", {"dbsize": bench.cli("DBSIZE"),
                                                 "version": bench.cli("INFO", "SERVER"),
                                                 "backlog_mb": options.backlog_mb or 8})
        for size in sizes:
            keys = (bench.FOOTPRINT // size // bench.CONNECTIONS) * bench.CONNECTIONS
            if (directory / f"{size}-set-c{levels[-1]}.result.json").exists():
                continue
            assert bench.cli("FLUSHALL", "SYNC") == "OK"
            assert bench.cli("DBSIZE") == "0"
            bench.run_client(directory, "FILL", size, keys, options.seconds)
            lengths = {f"kv_{key}": bench.cli("STRLEN", f"kv_{key}")
                       for key in (1, keys // 2, keys)}
            if bench.cli("DBSIZE") != str(keys) or set(lengths.values()) != {str(size)}:
                raise RuntimeError(f"Invalid dataset size={size} lengths={lengths}")
            bench.save(directory / f"{size}-validated.json",
                       {"keys": keys, "value_bytes": size, "lengths": lengths})
            for kind in options.kinds.split(","):
                if kind not in ("GET", "SET"):
                    raise ValueError(f"Unsupported operation {kind}")
                for connections in levels:
                    stem = f"{size}-{kind.lower()}-c{connections}"
                    if not (directory / f"{stem}.result.json").exists():
                        before = bench.cli("INFO", "STATS")
                        bench.run_client(directory, kind, size, keys, options.seconds,
                                         connections=connections, client_threads=16,
                                         sweep=True)
                        after = bench.cli("INFO", "STATS")
                        (directory / f"{stem}.info-before.txt").write_text(before + "\n")
                        (directory / f"{stem}.info-after.txt").write_text(after + "\n")
            if bench.cli("DBSIZE") != str(keys):
                raise RuntimeError(f"Key count changed for size {size}")
        bench.save(directory / "complete.json", {"time": time.time(), "sizes": sizes,
                                                 "levels": levels, "seconds": options.seconds})
    finally:
        if process.poll() is None:
            process.send_signal(signal.SIGTERM)
        process.wait(timeout=600)
        bench.save(directory / "server-exit.json", {"code": process.returncode})


if __name__ == "__main__":
    main()
