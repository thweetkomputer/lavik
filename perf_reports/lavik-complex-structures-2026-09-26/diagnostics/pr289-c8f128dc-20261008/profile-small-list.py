"""Profile the small-List regression without modifying the frozen harness."""
from pathlib import Path
import json

W = Path(__file__).parent
assert 'ALL_PR289_MEASUREMENTS_COMPLETE' in (W / 'benchmark.log').read_text()
# Reuse the frozen single-point executor and its checks, but do not execute its
# already completed clean grid or overwrite the original pre-measurement plan.
# This narrowly added diagnostic responds to the observed small-List variance.
prefix = (W / 'benchmark.py').read_text().split('\nrows = []\n', 1)[0]
prefix = prefix.replace("assert not (W / 'repeats.json').exists() and not (W / 'profiles.json').exists()",
                        "assert len(json.loads((W / 'repeats.json').read_text())['rows']) == 48")
prefix = prefix.replace("(W / 'protocol.json').write_text(json.dumps(method, indent=2) + '\\n')", '')
exec(compile(prefix, str(W / 'benchmark.py'), 'exec'))
profiles = json.loads((W / 'profiles.json').read_text())
assert len(profiles) == 6
for label in ['main', 'pr289']:
    row = point(label, 'list', 8388608, 'RPUSH_LPOP', 3, profiling=True)
    row['perf'] = str(next(Path(row['raw']).glob('*.perf')))
    profiles.append(row)
    (W / 'profiles.json').write_text(json.dumps(profiles, indent=2) + '\n')
assert len(profiles) == 8
print('SMALL_LIST_PROFILES_COMPLETE', flush=True)
