"""Use the report's client and server with explicit ZSet workload variants."""
import hashlib
import os
from pathlib import Path
import sys

sys.path.insert(0, os.environ['LAVIK_BENCH_ROOT'])
import run

operation = os.environ['PR283_OPERATION']
layout = os.environ.get('PR283_LAYOUT', 'distinct')
assert operation in ('SEED', 'ZSCORE', 'ZINCRBY', 'ZADD')
assert layout in ('distinct', 'ties')
run.OPS['zset'] = () if operation == 'SEED' else (operation,)
original_commands = run.command_lines
original_resp = run.resp
original_measure = run.measure
original_validate = run.validate


def resp(*args):
    # Only the local seed uses this encoder. Remote measured commands are
    # constructed below, so the seed mapping cannot rewrite measured scores.
    if layout == 'ties' and args[0] == 'ZADD':
        args = list(args)
        for index in range(2, len(args), 2):
            args[index] = 0
    return original_resp(*args)


def commands(op, field_bytes, entries):
    if op != 'ZADD':
        return original_commands(op, field_bytes, entries)
    positions = sorted({(entries - 1) * i // 7 for i in range(8)})
    # Explicit score toggles exercise actual ZADD source/boundary probes.
    # Concurrent random keys can repeat the existing score: report command
    # throughput, not a claim that every request changes a member's score.
    return [f'ZADD __key__ CH {score} {run.value(pos, field_bytes).decode()}'
            for score in (0, 1) for pos in positions]


def validate(kind, field_bytes, entries, keys, product, after=False):
    result = original_validate(kind, field_bytes, entries, keys, product, after)
    if layout == 'ties' and not after:
        for key in range(1, keys + 1):
            assert run.query('ZCOUNT', run.name(key), 0, 0) == entries
        result['all_members_initial_score'] = 0
    return result


def measure(directory, *args):
    run.save(directory / 'workload.json', {
        'operation': operation, 'layout': layout,
        'helper_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'zadd_semantics': 'CH, eight members, alternating score 0/1 commands; concurrent requests can be no-ops; no cardinality growth',
        'ties_semantics': 'Every seeded member has score zero; measured toggles can move selected members to score one',
    })
    original_measure(directory, *args)


run.resp = resp
run.command_lines = commands
run.validate = validate
run.measure = measure
run.main()
