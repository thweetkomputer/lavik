"""Three unprofiled long full-read repetitions; run.py handles lifecycle/validation."""

import sys
import run

original = run.measure
original_validate = run.validate
baseline = None


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
    assert op == run.FULL_OP[kind] and seconds == 30 and conns == 80
    for repeat in range(1, 4):
        dest = directory / f"repeat-{repeat}"
        dest.mkdir(exist_ok=True)
        original(dest, kind, size, field, entries, keys, op, conns, seconds, threads)


if __name__ == "__main__":
    if "--help" not in sys.argv:
        assert "--reuse-seeded-data" in sys.argv, "use one previously validated seed"
    run.measure = measure
    run.main()
