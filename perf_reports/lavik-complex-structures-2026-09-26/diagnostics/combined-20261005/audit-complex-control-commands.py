"""Check wire-command counters against completed complex-structure controls."""

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


# The Set workload alternates two wire commands. Its memtier request count is
# the sum of their calls, not a count of SADD/SREM pairs.
operations = {
    "HGET": ("hash", {"hget"}), "HSET": ("hash", {"hset"}),
    "SISMEMBER": ("set", {"sismember"}), "SADD_SREM": ("set", {"sadd", "srem"}),
    "LINDEX": ("list", {"lindex"}), "LSET": ("list", {"lset"}), "LRANGE": ("list", {"lrange"}),
    "ZSCORE": ("zset", {"zscore"}), "ZINCRBY": ("zset", {"zincrby"}),
    "XRANGE": ("stream", {"xrange"}), "XRANGE_FULL": ("stream", {"xrange"}),
    "XADD_MAXLEN": ("stream", {"xadd"}),
}
audits = []
identities = set()
for row in data["rows"]:
    assert "error" not in row and row["operation"] in operations
    kind, commands = operations[row["operation"]]
    assert row["type"] == kind
    identity = (row["tag"], row["operation"], row["connections"])
    assert identity not in identities, identity
    identities.add(identity)
    operation = row["operation"].lower()
    directory = args.report_root / "raw" / ("lavik-" + row["tag"])
    stem = f'{kind}-{row["logical_bytes"]}-{row["field_bytes"]}-{operation}-c{row["connections"]}'
    command_path = directory / f'{stem}.command.json'
    argv = json.loads(command_path.read_text())
    sent_commands = {value.removeprefix('--command=').split()[0].lower()
                     for value in argv if value.startswith('--command=')}
    assert sent_commands == commands, (identity, sent_commands, commands)
    client_path = directory / f'{stem}.json'
    client = json.loads(client_path.read_text())['ALL STATS']
    assert client['Totals']['Count'] == row['requests']
    assert client['Totals']['Connection Errors'] == 0
    assert str(client['Runtime']['Interrupted']).lower() == 'false'
    paths = {phase: directory / f"{stem}.info-{phase}.txt" for phase in ("before", "after")}
    before, after = (counters(paths[phase]) for phase in ("before", "after"))
    delta = {}
    for command in sorted(before.keys() | after.keys()):
        values = {
            key: after.get(command, {}).get(key, 0) - before.get(command, {}).get(key, 0)
            for key in ("calls", "rejected_calls", "failed_calls")
        }
        assert all(value >= 0 for value in values.values()), (identity, command, values)
        assert values["rejected_calls"] == values["failed_calls"] == 0, (identity, command, values)
        if any(values.values()):
            delta[command] = values
    assert all(delta.get(command, {}).get("calls", 0) > 0 for command in commands), (identity, delta)
    assert sum(delta[command]["calls"] for command in commands) == row["requests"] > 0, (identity, delta)
    # Setup and cardinality queries are outside the command workload. A seed
    # write or the opposite benchmark operation must not overlap this window.
    assert set(delta) <= commands | {"info"}, (identity, delta)
    audits.append({
        "tag": row["tag"],
        "operation": row["operation"],
        "connections": row["connections"],
        "requests": row["requests"],
        "wire_commands": sorted(commands),
        "client_sha256": hashlib.sha256(client_path.read_bytes()).hexdigest(),
        "command_sha256": hashlib.sha256(command_path.read_bytes()).hexdigest(),
        "command_deltas": delta,
        "info_sha256": {phase: hashlib.sha256(path.read_bytes()).hexdigest() for phase, path in paths.items()},
    })

assert audits
args.output.write_text(json.dumps({
    "input_sha256": hashlib.sha256(raw_input).hexdigest(),
    "auditor_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "observations": len(audits),
    "audits": audits,
    "scope": "All provided completed observations: exact client request count equals the sum of expected wire-command calls, no rejected/failed calls, no other command except INFO in each measurement window. Does not establish throughput causality or physical IO per command.",
}, indent=2) + "\n")
print(f"Verified command counters for {len(audits)} observations")
