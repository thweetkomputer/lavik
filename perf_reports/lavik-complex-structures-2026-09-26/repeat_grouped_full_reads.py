"""Three clean full-read repetitions, with optional separate --profile-full-read."""

import os
from pathlib import Path
import subprocess
import sys
import time
import run

original = run.measure
original_validate = run.validate
baseline = None
profile_enabled = "--profile-full-read" in sys.argv
if profile_enabled:
    sys.argv.remove("--profile-full-read")


def option(name):
    for i, arg in enumerate(sys.argv):
        if arg.startswith(name + "="):
            return arg.split("=", 1)[1]
        if arg == name:
            return sys.argv[i + 1]
    raise ValueError(name)


def profile(directory, kind, size, field, entries, keys, op, conns, seconds, threads):
    binary = option("--binary")
    pids = []
    for path in Path("/proc").iterdir():
        if not path.name.isdigit():
            continue
        try:
            command = (path / "cmdline").read_bytes().split(b"\0")
        except (OSError, PermissionError):
            continue
        if command[0] == os.fsencode(binary):
            pids.append(int(path.name))
    assert len(pids) == 1, pids
    destination = directory / "diagnostic-full"
    destination.mkdir(exist_ok=True)
    argv = [
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
        str(destination / "cpu.perf"),
        "--",
        "sleep",
        "20",
    ]
    run.save(
        destination / "profile-provenance.json",
        {
            "source_commit": option("--source-commit"),
            "binary": binary,
            "pid": pids[0],
            "argv": argv,
            "time": time.time(),
            "operation": op,
            "connections": conns,
        },
    )
    with (destination / "perf.log").open("w") as log:
        process = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT)
        try:
            original(
                destination,
                kind,
                size,
                field,
                entries,
                keys,
                op,
                conns,
                seconds,
                threads,
            )
        finally:
            code = process.wait(timeout=40)
        assert code == 0, code
    for name, mode in [("self", "--no-children"), ("inclusive", "--children")]:
        output = subprocess.check_output(
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
                str(destination / "cpu.perf"),
            ],
            text=True,
        )
        # perf pads symbol columns to the longest coroutine symbol.
        (destination / f"{name}.txt").write_text(
            "\n".join(" ".join(line.split()) for line in output.splitlines()) + "\n"
        )


def validate(kind, field, entries, keys, product, after=False):
    global baseline
    # Existing SADD/SREM data may retain the benchmark's one toggled member.
    # Full reads must preserve the exact per-key cardinalities, not just a range.
    result = original_validate(
        kind, field, entries, keys, product, after=True if kind == "set" else after
    )
    counts = result["sample_cardinalities"]
    if baseline is None:
        baseline = counts
    else:
        assert counts == baseline, "full-read workload changed cardinalities"
    return result


run.validate = validate


def measure(directory, kind, size, field, entries, keys, op, conns, seconds, threads):
    assert op == run.FULL_OP[kind] and seconds == 30
    for repeat in range(1, 4):
        dest = directory / f"repeat-{repeat}"
        dest.mkdir(exist_ok=True)
        original(dest, kind, size, field, entries, keys, op, conns, seconds, threads)
    if profile_enabled:
        profile(
            directory, kind, size, field, entries, keys, op, conns, seconds, threads
        )


if __name__ == "__main__":
    if "--help" not in sys.argv:
        assert "--reuse-seeded-data" in sys.argv, "use one previously validated seed"
    run.measure = measure
    run.main()
