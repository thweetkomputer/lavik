#!/usr/bin/env python3
"""Resume a stopped Lavik grid on its retained, independently validated seed.

Prepare the same SPDK devices without discarding them first. Existing successful
and failed observations stay untouched; the restart boundary is recorded. This
is for a cleanly stopped server, not recovery from data loss or process failure.
"""
from pathlib import Path
import hashlib
import json
import os
import signal
import subprocess
import sys
import time

sys.path.insert(0, os.environ.get("LAVIK_BENCH_ROOT", str(Path(__file__).resolve().parent)))
import run


def main():
    tag = sys.argv[1]
    assert Path(tag).name == tag and tag.startswith("lavik-")
    directory = run.ROOT / "raw" / tag
    assert not (directory / "complete.json").exists()
    assert not (directory / "resume.json").exists()
    assert json.loads((directory / "server-exit.json").read_text())["code"] == 0
    files = list(directory.glob("provenance-*.json"))
    assert len(files) == 1
    proof = json.loads(files[0].read_text())
    assert proof["mode"] == "both"
    assert len(proof["types"]) == len(proof["sizes"]) == len(proof["fields"]) == 1
    argv = json.loads((directory / "server-command.json").read_text())
    assert argv[:6] == ["prlimit", "--memlock=unlimited:unlimited",
                        "--nofile=65535:65535", "taskset", "-c", "0-15"]
    assert argv[6] == proof["binary"]
    assert hashlib.sha256(Path(proof["binary"]).read_bytes()).hexdigest() == proof["sha256"]
    run.spdk_host.assert_driver("vfio-pci")
    kind, size, field = proof["types"][0], proof["sizes"][0], proof["fields"][0]
    keys, entries = proof["keys"], size // field
    combo = f"{kind}-{size}-{field}"
    assert (directory / f"{combo}.fill.json").exists()
    assert (directory / f"{combo}.validated.json").exists()
    # Require every prior memtier observation to have an explicit outcome.
    # An exception-only observation must be classified from its saved output
    # before resuming, so a failed point cannot silently become a retry.
    for path in directory.glob(combo + "-*.command.json"):
        stem = path.name.removesuffix(".command.json")
        assert ((directory / (stem + ".result.json")).exists() or
                (directory / (stem + ".error.json")).exists()), stem
    try:
        run.query("PING")
    except (OSError, EOFError):
        pass
    else:
        raise RuntimeError("benchmark port occupied")
    run.save(directory / "resume.json", {
        "time": time.time(), "reason": "Continue missing points after a recorded admission failure",
        "retained_seed": True, "reseeded": False,
        "previous_server_exit": json.loads((directory / "server-exit.json").read_text()),
        "source_commit": proof["source_commit"], "sha256": proof["sha256"],
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "existing_results": sorted(p.name for p in directory.glob("*.result.json")),
        "existing_errors": sorted(p.name for p in directory.glob("*.error.json"))})
    with (directory / "resume-server.log").open("w") as output:
        proc = subprocess.Popen(argv, stdout=output, stderr=subprocess.STDOUT)
    try:
        for _ in range(6000):
            if proc.poll() is not None:
                raise RuntimeError("server exited during resumed startup")
            try:
                if run.query("PING") == b"PONG":
                    break
            except (OSError, EOFError):
                pass
            time.sleep(.2)
        else:
            raise TimeoutError("resumed startup")
        run.save(directory / f"{combo}.resumed-validated.json",
                 run.validate(kind, field, entries, keys, "lavik", after=True))
        failures = 0
        for op in (run.FULL_OP[kind], *run.OPS[kind]):
            levels = proof["full_levels"] if op == run.FULL_OP[kind] else proof["levels"]
            for conns in levels:
                stem = f"{combo}-{op.lower()}-c{conns}"
                failure = directory / (stem + ".error.json")
                if (directory / (stem + ".result.json")).exists() or failure.exists():
                    continue
                try:
                    run.measure(directory, kind, size, field, entries, keys, op,
                                conns, proof["seconds"], min(proof["client_threads"], conns))
                except Exception as exc:
                    if proc.poll() is not None:
                        raise
                    run.save(failure, {"product": "lavik", "type": kind,
                                      "logical_bytes": size, "field_bytes": field,
                                      "operation": op, "connections": conns,
                                      "error": str(exc), "time": time.time()})
                    failures += 1
        run.save(directory / f"{combo}.after.json",
                 run.validate(kind, field, entries, keys, "lavik", after=True))
        run.save(directory / f"{combo}.complete.json", {"time": time.time()})
        run.save(directory / "complete.json", {"time": time.time(),
                 "failures_in_this_run": failures,
                 "failures_total": len(list(directory.glob("*.error.json"))),
                 "resumed": True})
    finally:
        if proc.poll() is None:
            proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=600)
        run.save(directory / "server-exit.json", {"code": proc.returncode})


if __name__ == "__main__":
    main()
