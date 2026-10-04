#!/usr/bin/env python3
"""Use per-command RESP encoding for the historical batched-import workload.

Run with run.py's options. LAVIK_BENCH_ROOT can point to a separate run.py/raw
workspace. Keep this workload distinct from RESTORE and shared-wire-template
client measurements; it includes Python client encoding time.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import os
import sys
import time

sys.path.insert(0, os.environ.get("LAVIK_BENCH_ROOT", str(Path(__file__).resolve().parent)))
import run


def fill(kind, field_bytes, entries, keys, pipeline, workers, target_bytes):
    assert kind in ("hash", "set")
    begin = time.monotonic()
    seed_values = tuple(run.value(i, field_bytes) for i in range(entries))
    seed_fields = tuple(f"f{i:08d}" for i in range(entries)) if kind == "hash" else ()
    # Match the original peers' per-command encoding. Only immutable operand
    # bytes are shared; do not introduce pre-encoded RESP batch templates.
    with ThreadPoolExecutor(max_workers=workers) as pool:
        jobs = [pool.submit(run.fill_worker, kind, field_bytes, entries,
                            range(i + 1, keys + 1, workers), pipeline,
                            seed_values, seed_fields, target_bytes, None)
                for i in range(workers)]
        commands = sum(job.result() for job in jobs)
    step = run.seed_step(kind, field_bytes, target_bytes)
    assert commands == keys * ((entries + step - 1) // step)
    return {"seconds": time.monotonic() - begin, "commands": commands,
            "entries_per_command": step, "client_encoding": "per-command"}


if __name__ == "__main__":
    run.fill = fill
    run.main()
