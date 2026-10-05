"""Validate the frozen 150-point combination; summarize only its complete matrix."""

import argparse
import hashlib
import json
import math
import statistics
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--input", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--report-root", type=Path, required=True)
parser.add_argument("--validate-only", action="store_true")
args = parser.parse_args()
raw_input = args.input.read_bytes()
data = json.loads(raw_input)
versions = data["versions"]
heads = {
    "main": "4610d6077e8e32d59639a5ee88dbe8cbd305aab2",
    "combined": "78e29277618f4ef40ccefab0930cbab667a0a40e",
}
assert set(versions) == set(heads)
for label, head in heads.items():
    version = versions[label]
    assert version["commit"] == head
    assert version["bycorf_commit"] == "62509c93d40c2480f5046b71454db6cf95801b04"
    assert all(t["tests"] > 0 and t["failures"] == 0 for t in version["tests"].values())
    assert version["pubsub_exit"] == 0
    options = version["comparison_build_options"]
    assert options == versions["main"]["comparison_build_options"]
    assert options["BUILD_TESTING"] == options["LAVIK_ENABLE_TEST_FAULTS"] == "OFF"
    assert options["LAVIK_MARCH"] == "native"

# Fix the complete protocol independently of the mutable observation manifest.
conditions = [
    ("stream", 104857600, 128, 8, {"XRANGE": [2560], "XRANGE_FULL": [1, 4, 16], "XADD_MAXLEN": [320, 5120]}),
    ("stream", 65536, 1024, 64, {"XRANGE": [5120], "XRANGE_FULL": [80], "XADD_MAXLEN": [2560, 5120]}),
    ("stream", 104857600, 1024, 8, {"XADD_MAXLEN": [80, 320, 5120]}),
    ("zset", 104857600, 1024, 8, {"ZSCORE": [80, 320, 5120], "ZINCRBY": [80, 320, 5120]}),
    ("zset", 65536, 128, 64, {"ZSCORE": [80, 320, 5120], "ZINCRBY": [80, 320, 5120]}),
]
expected = {
    (kind, size, field, keys, operation, connections)
    for kind, size, field, keys, operations in conditions
    for operation, levels in operations.items()
    for connections in levels
}
assert len(expected) == 25
fields = ["type", "logical_bytes", "field_bytes", "keys", "operation", "connections"]


def case(row):
    return tuple(row[field] for field in fields)


def read(path):
    return json.loads(path.read_text())


def source(directory):
    paths = list(directory.glob("provenance-*.json"))
    assert len(paths) == 1, directory
    return read(paths[0])


def clean_exit(directory):
    assert read(directory / "server-exit.json")["code"] == 0
    assert read(directory / "complete.json")["failures_total"] == 0
    assert not list(directory.glob("*.error.json"))


rows = data["rows"]
assert rows
groups, proofs, seed_proofs = {}, {}, {}
orders = [("main", "combined"), ("combined", "main"), ("main", "combined")]
for row in rows:
    key = case(row)
    assert key in expected and "error" not in row
    identity = (row["round"], row["version"])
    assert identity in {(n, label) for n in (1, 2, 3) for label in versions}
    assert identity not in groups.setdefault(key, {})
    groups[key][identity] = row
    assert row["seconds"] == 30 and row["requests"] > 0
    assert row["entries_per_key"] == row["logical_bytes"] // row["field_bytes"]
    assert all(math.isfinite(row[m]) and row[m] > 0 for m in ("qps", "p99_ms"))
    directory = args.report_root / "raw" / ("lavik-" + row["tag"])
    points = [read(p) for p in directory.glob("*.result.json")]
    matches = [point for point in points if case(point) == key]
    assert len(matches) == 1 and all(row.get(k) == v for k, v in matches[0].items())
    if row["tag"] in proofs:
        continue
    clean_exit(directory)
    origin = source(directory)
    version = versions[row["version"]]
    assert origin["source_commit"] == version["commit"] and origin["sha256"] == version["sha256"]
    prefix = f'{row["type"]}-{row["logical_bytes"]}-{row["field_bytes"]}'
    before = read(directory / (prefix + ".validated.json"))["sample_cardinalities"]
    after = read(directory / (prefix + ".after.json"))["sample_cardinalities"]
    assert set(before) == set(after) == {f"complex_{i}" for i in range(1, row["keys"] + 1)}
    assert all(n == row["entries_per_key"] for n in before.values())
    if row["operation"] == "XADD_MAXLEN":
        # Preserve the queued driver's approximate MAXLEN overshoot bound.
        assert all(before[k] <= after[k] <= before[k] + 100 for k in before)
    else:
        assert before == after
    fill = read(directory / (prefix + ".fill.json"))
    seed_tag = fill.get("reused_seed_from")
    assert origin.get("reused_seed_from") == seed_tag
    if row["operation"] in ("XADD_MAXLEN", "ZINCRBY"):
        assert seed_tag is None
    else:
        assert seed_tag
        claims = [s for s in data["seeds"] if s["tag"] == seed_tag]
        assert len(claims) == 1
        assert claims[0]["round"] == row["round"] and claims[0]["cardinalities"] == before
        seed = args.report_root / "raw" / ("lavik-" + seed_tag)
        clean_exit(seed)
        assert not list(seed.glob("*.result.json"))
        seed_origin = source(seed)
        assert seed_origin["source_commit"] == versions["main"]["commit"]
        assert seed_origin["sha256"] == versions["main"]["sha256"]
        assert seed_origin.get("reused_seed_from") is None
        for suffix in (".validated.json", ".after.json"):
            assert read(seed / (prefix + suffix))["sample_cardinalities"] == before
        seed_proofs[seed_tag] = {"source_commit": seed_origin["source_commit"], "sha256": seed_origin["sha256"], "cardinalities": before}
    proofs[row["tag"]] = {"source_commit": origin["source_commit"], "sha256": origin["sha256"], "seed_tag": seed_tag, "before": before, "after": after, "server_exit": 0}

# Each complete condition retains the executed A/B, B/A, A/B order. Partial
# validation permits only a prefix, never a missing first version in a round.
for key, observations in groups.items():
    for n, order in enumerate(orders, 1):
        observed = [label for round_, label in observations if round_ == n]
        assert observed == list(order[:len(observed)]), (key, n, observed)

summary = []
if not args.validate_only:
    assert len(rows) == 150 and set(groups) == expected, "incomplete comparison"
    for key, observations in sorted(groups.items()):
        assert set(observations) == {(n, label) for n in (1, 2, 3) for label in versions}
        pairs = []
        for n in (1, 2, 3):
            parent, candidate = observations[(n, "main")], observations[(n, "combined")]
            if key[4] not in ("XADD_MAXLEN", "ZINCRBY"):
                assert proofs[parent["tag"]]["seed_tag"] == proofs[candidate["tag"]]["seed_tag"]
            pairs.append({"round": n, "main": {k: parent[k] for k in ("tag", "qps", "p99_ms", "requests")}, "combined": {k: candidate[k] for k in ("tag", "qps", "p99_ms", "requests")}, "qps_change_percent": (candidate["qps"] / parent["qps"] - 1) * 100, "p99_change_percent": (candidate["p99_ms"] / parent["p99_ms"] - 1) * 100})
        entry = dict(zip(fields, key))
        entry["pairs"] = pairs
        for metric in ("qps", "p99"):
            changes = [p[metric + "_change_percent"] for p in pairs]
            entry[metric + "_paired_percent"] = {"median": statistics.median(changes), "min": min(changes), "max": max(changes), "positive_pairs": sum(x > 0 for x in changes), "negative_pairs": sum(x < 0 for x in changes)}
        for label in versions:
            entry[label + "_median_qps"] = statistics.median(p[label]["qps"] for p in pairs)
            entry[label + "_median_p99_ms"] = statistics.median(p[label]["p99_ms"] for p in pairs)
        summary.append(entry)

result = {
    "input_sha256": hashlib.sha256(raw_input).hexdigest(),
    "validator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "observations": len(rows), "expected_observations": 150,
    "status": "Available completed observations verified; no partial performance conclusion" if args.validate_only else "Complete 150-point comparison verified",
    "versions": versions, "method": data["method"], "proofs": proofs,
    "seed_proofs": seed_proofs, "summary": summary,
    "limitations": "Three pairs are not confidence intervals. Median paired ratios differ from ratios of marginal medians. Shared logical read seeds are not immutable physical snapshots. Write populations are independent. Full reads issue few requests. This frozen PR265/266/270 combination excludes later drafts; individual gains must not be summed. Historical peers were not rerun; no overall parity claim.",
}
args.output.write_text(json.dumps(result, indent=2) + "\n")
print(result["status"], len(rows), "/ 150")
