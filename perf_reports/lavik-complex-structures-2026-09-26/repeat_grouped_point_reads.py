"""Run three clean 30-second point-read repeats on an existing Hash/Set dataset."""

from pathlib import Path
import sys

import run

original_measure = run.measure
original_validate = run.validate
baseline = None


def validate(kind, field, entries, keys, product, after=False):
    global baseline
    # A prior SADD/SREM grid may leave one toggled member. Reads must preserve
    # the exact per-key cardinalities observed at the start of this run.
    result = original_validate(
        kind, field, entries, keys, product, after=True if kind == "set" else after
    )
    counts = result["sample_cardinalities"]
    if baseline is None:
        baseline = counts
    else:
        assert counts == baseline, "read-only workload changed cardinalities"
    return result


def measure(directory, kind, size, field, entries, keys, op, conns, seconds, threads):
    assert kind in ("hash", "set") and op in ("HGET", "SISMEMBER")
    assert seconds == 30
    for repeat in range(1, 4):
        dest = Path(directory) / f"repeat-{repeat}"
        dest.mkdir(exist_ok=True)
        original_measure(
            dest, kind, size, field, entries, keys, op, conns, seconds, threads
        )


if __name__ == "__main__":
    if "--help" not in sys.argv:
        assert "--reuse-seeded-data" in sys.argv, "use one validated dataset"
    # run.py's point mode normally includes writes. Omit those explicitly so
    # main and PR can recover precisely the same unchanged logical dataset.
    run.OPS = {kind: (ops[0],) for kind, ops in run.OPS.items()}
    run.validate = validate
    run.measure = measure
    run.main()
