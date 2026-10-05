"""Check command counters against completed ZSet benchmark observations."""

import argparse
import hashlib
import json
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--input", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument(
    "--report-root",
    type=Path,
    default=Path("/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26"),
)
args = parser.parse_args()
raw_input = args.input.read_bytes()
data = json.loads(raw_input)


def counters(path):
    result = {}
    for line in path.read_text().splitlines():
        if not line.startswith("cmdstat_"):
            continue
        command, fields = line.split(":", 1)
        command = command.removeprefix("cmdstat_")
        assert command not in result, (path, command)
        fields = dict(field.split("=", 1) for field in fields.split(","))
        result[command] = {
            key: int(fields[key])
            for key in ("calls", "rejected_calls", "failed_calls")
        }
    assert result, path
    return result


audits = []
identities = set()
for row in data["rows"]:
    assert "error" not in row and row["operation"] in ("ZSCORE", "ZINCRBY")
    identity = (row["tag"], row["operation"], row["connections"])
    assert identity not in identities, identity
    identities.add(identity)
    operation = row["operation"].lower()
    directory = args.report_root / "raw" / ("lavik-" + row["tag"])
    stem = f'zset-{row["logical_bytes"]}-{row["field_bytes"]}-{operation}-c{row["connections"]}'
    paths = {phase: directory / f"{stem}.info-{phase}.txt" for phase in ("before", "after")}
    before, after = (counters(paths[phase]) for phase in ("before", "after"))
    delta = {}
    for command in before.keys() | after.keys():
        values = {
            key: after.get(command, {}).get(key, 0) - before.get(command, {}).get(key, 0)
            for key in ("calls", "rejected_calls", "failed_calls")
        }
        assert all(value >= 0 for value in values.values()), (identity, command, values)
        assert values["rejected_calls"] == values["failed_calls"] == 0, (identity, command, values)
        if any(values.values()):
            delta[command] = values
    assert delta[operation]["calls"] == row["requests"] > 0, (identity, delta)
    # Setup and cardinality queries are outside the command workload. A seed
    # write or the opposite benchmark operation must not overlap this window.
    assert set(delta) <= {operation, "info"}, (identity, delta)
    audits.append({
        "tag": row["tag"],
        "operation": row["operation"],
        "connections": row["connections"],
        "requests": row["requests"],
        "command_deltas": delta,
        "info_sha256": {phase: hashlib.sha256(path.read_bytes()).hexdigest() for phase, path in paths.items()},
    })

assert audits
args.output.write_text(json.dumps({
    "input_sha256": hashlib.sha256(raw_input).hexdigest(),
    "auditor_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "observations": len(audits),
    "audits": audits,
    "scope": "All provided completed observations: exact workload call count, no rejected/failed calls, no other command except INFO in each measurement window. Does not establish throughput causality or physical IO per command.",
}, indent=2) + "\n")
print(f"Verified command counters for {len(audits)} observations")
