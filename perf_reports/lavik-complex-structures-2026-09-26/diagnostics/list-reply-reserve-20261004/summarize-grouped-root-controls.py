"""Validate the frozen 72-point ordinary-key root-reuse controls; require the complete matrix."""

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
    "parent": "19496654cc43b21df11fb59be60e174dc4c89dbc",
    "candidate": "28d7cca498655e02f46407adb65335219b10ee6b",
}
assert set(versions) == set(heads)
for label, head in heads.items():
    version = versions[label]
    assert version["commit"] == head
    assert version["bycorf_commit"] == "62509c93d40c2480f5046b71454db6cf95801b04"
    assert all(t["tests"] > 0 and t["failures"] == 0 for t in version["ordinary_tests"].values())
    options = version["comparison_build_options"]
    assert options == versions["parent"]["comparison_build_options"]
    assert options["BUILD_TESTING"] == options["LAVIK_ENABLE_TEST_FAULTS"] == "OFF"
    assert options["LAVIK_MARCH"] == "native"
    expected_tests = {"hash-tests", "ordered-tests", "blocking-tests"}
    if label == "candidate":
        expected_tests.add("unit-tests")
    assert set(version["ordinary_tests"]) == expected_tests
    assert all(t.get("errors", 0) == 0 for t in version["ordinary_tests"].values())
    if label == "parent":
        assert version["full_ci_conclusion"] == "failure"
        assert version["full_fault_enabled_ci"].endswith("/actions/runs/37237724710")
        limitation = version["full_ci_limitation"]
        assert limitation["failed_job"] == 111541360623
        assert limitation["case"] == "lavik_redis_sync_reader_cluster-cluster"
        assert limitation["log_sha256"] == "6a9fc94d439772984caf4b706c12f43b0c61b21c828783db0396c73ed16b50e5"
    else:
        assert version["full_ci_conclusion"] == "success"
        assert version["full_ci_limitation"] is None

# Fix the complete protocol independently of the mutable observation manifest.
conditions = [
    ("hash", 1048576, 128, 500, {"HGET": [320], "HSET": [320]}),
    ("set", 1048576, 128, 500, {"SISMEMBER": [320], "SADD_SREM": [320]}),
    ("list", 65536, 128, 64, {"LINDEX": [320], "LRANGE": [80], "LSET": [320]}),
    ("zset", 65536, 128, 64, {"ZSCORE": [320], "ZINCRBY": [320]}),
    ("stream", 65536, 1024, 64, {"XRANGE": [320], "XRANGE_FULL": [80], "XADD_MAXLEN": [320]}),
]
expected = {
    (kind, size, field, keys, operation, connections)
    for kind, size, field, keys, operations in conditions
    for operation, levels in operations.items()
    for connections in levels
}
assert len(expected) == 12
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
orders = [("parent", "candidate"), ("candidate", "parent"), ("parent", "candidate")]
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
    elif row["operation"] == "SADD_SREM":
        # Concurrent alternating operations may leave the one temporary member.
        assert all(after[k] in (before[k], before[k] + 1) for k in before)
    else:
        assert before == after
    fill = read(directory / (prefix + ".fill.json"))
    seed_tag = fill.get("reused_seed_from")
    assert origin.get("reused_seed_from") == seed_tag
    if row["operation"] in ("HSET", "SADD_SREM", "LSET", "ZINCRBY", "XADD_MAXLEN"):
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
        assert seed_origin["source_commit"] == versions["parent"]["commit"]
        assert seed_origin["sha256"] == versions["parent"]["sha256"]
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
    assert len(rows) == 72 and set(groups) == expected, "incomplete comparison"
    for key, observations in sorted(groups.items()):
        assert set(observations) == {(n, label) for n in (1, 2, 3) for label in versions}
        pairs = []
        for n in (1, 2, 3):
            parent, candidate = observations[(n, "parent")], observations[(n, "candidate")]
            if key[4] not in ("HSET", "SADD_SREM", "LSET", "ZINCRBY", "XADD_MAXLEN"):
                assert proofs[parent["tag"]]["seed_tag"] == proofs[candidate["tag"]]["seed_tag"]
            pairs.append({"round": n, "parent": {k: parent[k] for k in ("tag", "qps", "p99_ms", "requests")}, "candidate": {k: candidate[k] for k in ("tag", "qps", "p99_ms", "requests")}, "qps_change_percent": (candidate["qps"] / parent["qps"] - 1) * 100, "p99_change_percent": (candidate["p99_ms"] / parent["p99_ms"] - 1) * 100})
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
    "observations": len(rows), "expected_observations": 72,
    "status": "Available completed observations verified; no partial performance conclusion" if args.validate_only else "Complete 72-point ordinary-key comparison verified",
    "versions": versions, "method": data["method"], "proofs": proofs,
    "seed_proofs": seed_proofs, "summary": summary,
    "limitations": "Three pairs are not confidence intervals. Median paired ratios differ from ratios of marginal medians. Shared logical read seeds are not immutable physical snapshots. Write populations are independent. This frozen parent194/candidate28 comparison covers ordinary short keys only. Hash/Set use500 keys rather than the historical50000-key grid. It does not measure giant-key latency, validate a new rebased head, or establish overall parity. Historical peers were not rerun. Parent full CI remains failed due to the reviewed source Redis cluster-bus port collision; that import scenario is not validated by these ordinary-key controls.",
}
args.output.write_text(json.dumps(result, indent=2) + "\n")
print(result["status"], len(rows), "/ 72")
