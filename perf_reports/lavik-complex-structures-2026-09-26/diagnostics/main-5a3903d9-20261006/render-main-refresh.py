"""Select only completed new-main grids and render reproducible report inputs."""
from pathlib import Path
import importlib.util
import json
import shutil
import subprocess
import sys

W = Path(__file__).parent
R = Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26')
assert 'ALL_MAIN_GRIDS_AND_IMPORTS_COMPLETE' in (W / 'main-refresh-driver.log').read_text()
V = json.loads((W / 'versions.json').read_text())['main']
assert V['commit'] == '5a3903d9b3c0632e3b34e827b779d9daa58455c2'
D = R / 'diagnostics/main-5a3903d9-20261006'
D.mkdir(exist_ok=True)


def read(path):
    return json.loads(path.read_text())


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def verify(tag):
    raw = R / 'raw' / ('lavik-' + tag)
    assert read(raw / 'server-exit.json')['code'] == 0
    assert read(raw / 'complete.json')['failures_total'] == len(list(raw.glob('*.error.json')))
    proofs = list(raw.glob('provenance-*.json'))
    assert len(proofs) == 1
    p = read(proofs[0])
    assert p['source_commit'] == V['commit'] and p['sha256'] == V['sha256']
    if not tag.startswith('seed-'):
        shutil.copyfile(W / (tag + '-host.json'), D / (tag + '-host.json'))


for name in ('current-main.json', 'current-imports.json'):
    shutil.copyfile(W / ('previous-' + name), D / ('previous-' + name))
    manifest = read(W / ('previous-' + name))
    manifest.update(target_main=V['commit'], date='2026-10-06',
                    build_proof=str((D / 'host-and-build.json').relative_to(R)))
    manifest['merged_prs'] = sorted(set(manifest['merged_prs']) | {265, 266, 267, 268, 270, 280})
    for row in manifest['plots']:
        category = 'import' if name == 'current-imports.json' else row['category']
        tag = f'main{V["commit"][:8]}-{category}-{row["kind"]}-{row["size"]}-k{row["keys"]}-f{row["field"]}-20261006'
        verify(tag)
        row['main'] = {'tag': tag, 'commit': V['commit'], 'sha256': V['sha256'], 'fresh': True}
        row['variants'] = []
        if category == 'hashset':
            verify('seed-' + tag)
            row['main']['seed_tag'] = 'seed-' + tag
    save(R / name, manifest)
save(D / 'host-and-build.json', {'build': V, 'cpu': json.loads(subprocess.check_output(['lscpu', '-J'])),
                               'peer_measurements': 'Historical matched workloads, not rerun; persistence/cache settings differ.'})
shutil.copyfile(W / 'pr283-parent-CMakeCache.txt', D / 'CMakeCache.txt')
for name in ('run-condition.py', 'run-import.py', 'host.py', 'private-tmp-exec.py',
             'refresh-main.py', 'render-main-refresh.py', 'commands.jsonl',
             'main-refresh-driver.log', 'main-refresh-progress.json'):
    shutil.copyfile(W / name, D / name)

# Use the existing plot/data validation code. The introductory evidence is
# maintained independently of generated chart sections, so rerendering must
# not resurrect old draft/merged or performance-validation claims.
spec = importlib.util.spec_from_file_location('plot', R / 'plot_current_main.py')
plot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plot)
manifest = read(R / 'current-main.json')
for row in manifest['plots']:
    plot.draw(row)
    if row['category'] == 'lset':
        plot.draw_list_fill(row)
imports = read(R / 'current-imports.json')
for row in imports['plots']:
    v = row['main']
    subprocess.run([sys.executable, str(R / 'plot_fill_reference.py'), row['kind'],
                    '--size', str(row['size']), '--field', str(row['field']),
                    '--lavik-tag', v['tag'], '--lavik-commit', v['commit'],
                    '--lavik-sha256', v['sha256'], '--lavik-label', 'Lavik main ' + v['commit'][:8]], check=True)
    row.update(chart_commit=v['commit'], chart_tag=v['tag'])
save(R / 'current-imports.json', imports)

# Keep the older source manifests usable by their dedicated plot scripts.
# Their previous selections remain in this diagnostic's snapshots.
for name, category in (('published-main.json', 'hashset'),
                       ('lset-large-published.json', 'lset'),
                       ('ordered-published.json', 'ordered')):
    legacy = read(R / name)
    # A rerender must retain the original selection, not snapshot its own
    # already-updated output as the historical baseline.
    previous = D / ('previous-' + name)
    if not previous.exists():
        save(previous, legacy)
    if 'main_as_of' in legacy:
        legacy['main_as_of'] = V['commit']
    for old in legacy['plots']:
        matches = [row for row in manifest['plots']
                   if row['category'] == category and row['size'] == old['size']
                   and (category == 'lset' or
                        (row['kind'], row['field']) == (old['kind'], old['field']))]
        assert len(matches) == 1, (name, old)
        version = matches[0]['main']
        if category == 'hashset':
            old.update(tag=version['tag'], measured_commit=V['commit'],
                       sha256=V['sha256'], label='Lavik main',
                       seed_tag=version['seed_tag'])
        else:
            old['main'] = dict(version)
    save(R / name, legacy)

for zh, name in ((True, 'README.zh-CN.md'), (False, 'README.md')):
    generated = plot.readme(manifest, zh)
    # Keep the generated chart portion separate for review before replacing
    # the report. Its headings, raw links and failures all use new metadata.
    (W / ('generated-main-' + name)).write_text(generated)
print('All new-main plots and source selections rendered; review introduction before publication.')
