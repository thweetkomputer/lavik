"""Publish large write controls only after exact driver success and host restore."""
from pathlib import Path
import json
import shutil
import statistics
import subprocess
import time

W = Path(__file__).parent
repo = Path('/mnt/dev/lavik-complex-refresh-20261004')
R = repo / 'perf_reports/lavik-complex-structures-2026-09-26'
D = R / 'diagnostics/stream-reply-20261004'
proc = Path('/proc/586587/stat')
identity = proc.read_text().split()[21] if proc.exists() else None
print('WAIT_FOR_COMPLETE_CONTROLS', identity, flush=True)
while proc.exists() and identity is not None:
    try:
        if proc.read_text().split()[21] != identity:
            break
    except FileNotFoundError:
        break
    time.sleep(15)
assert 'ALL_STREAM_REPLY_CONTROL_REPEATS_COMPLETE' in (W / 'stream-reply-control-repeat-driver.log').read_text()
v = json.loads((W / 'stream-reply-control-repeats.json').read_text())
assert len(v['rows']) == 36
rows = [x for x in v['rows'] if x['logical_bytes'] == 104857600]
assert len(rows) == 12
large = {'main': v['main'], 'candidate': v['candidate'], 'rows': rows, 'seeds': [],
         'method': 'Three 30-second pairs A/B, B/A, A/B for 100MiB/128B/8keys. XADD_MAXLEN c320/c5120 with independent fresh seeds per binary; immutable a565d603 and 1e87107e. No builds/tests/perf overlap. Errors are retained.'}
summary = []
for op, c in [('XADD_MAXLEN', 320), ('XADD_MAXLEN', 5120)]:
    pairs = []
    for n in (1, 2, 3):
        pair = {x['version']: x for x in rows if (x['operation'], x['connections'], x['round']) == (op, c, n)}
        assert set(pair) == {'main', 'candidate'}
        a, b = pair['main'], pair['candidate']
        failed = 'error' in a or 'error' in b
        pairs.append({'round': n, **pair,
                      'qps_change_percent': None if failed else 100 * (b['qps'] / a['qps'] - 1),
                      'p99_change_percent': None if failed else 100 * (b['p99_ms'] / a['p99_ms'] - 1)})
    qps = [p['qps_change_percent'] for p in pairs if p['qps_change_percent'] is not None]
    tails = [p['p99_change_percent'] for p in pairs if p['p99_change_percent'] is not None]
    summary.append({'operation': op, 'connections': c, 'pairs': pairs,
                    'median_paired_qps_change_percent': statistics.median(qps) if len(qps) == 3 else None,
                    'qps_change_range_percent': [min(qps), max(qps)] if qps else None,
                    'median_paired_p99_change_percent': statistics.median(tails) if len(tails) == 3 else None,
                    'p99_change_range_percent': [min(tails), max(tails)] if tails else None})
assert subprocess.check_output(['git', 'diff', '--cached', '--name-only'], cwd=repo) == b'', 'unrelated staged changes'
files = []
for name, value in [('stream-reply-large-write-control-repeats.json', large),
                    ('stream-reply-large-write-control-summary.json', {'main': v['main'], 'candidate': v['candidate'], 'rows': summary, 'method': large['method']})]:
    p = D / name
    p.write_text(json.dumps(value, indent=2) + '\n')
    files.append(p)
for name in ['publish-stream-reply-large-write-controls.py', 'repeat-stream-reply-controls.py']:
    p = D / name
    shutil.copyfile(W / name, p)
    files.append(p)
for tag in sorted({x['tag'] for x in rows} | {x['tag'] for x in large['seeds']}):
    raw = R / 'raw' / ('lavik-' + tag)
    assert json.loads((raw / 'server-exit.json').read_text())['code'] == 0
    assert (raw / 'complete.json').exists()
    label = next(x['version'] for x in rows if x['tag'] == tag)
    proof = json.loads(next(raw.glob('provenance-*.json')).read_text())
    assert proof['source_commit'] == v[label]['commit'] and proof['sha256'] == v[label]['sha256']
    files.extend(raw.glob('*.json'))
section = '''## 三轮大数据写入控制复测

100 MiB / 128 B / 8 keys，每点 30 秒，交替 A/B、B/A、A/B。每个版本独立新建数据，保留所有错误和尾延迟；这是初测写入退化的配对核查，不把读取收益归给写入。即使复测某项改善，也不掩盖上面的小数据高并发写入 p99 退化。

[全部 12 个观测](stream-reply-large-write-control-repeats.json) · [逐对变化及汇总](stream-reply-large-write-control-summary.json)。仍使用固定 `a565d603` / `1e87107e` 二进制，并非新 main 或后续 PR 的性能。

| 命令 | 并发 | QPS 变化中位数 | 三轮 QPS 变化范围 | p99 变化中位数 | 三轮 p99 变化范围 |
|---|---:|---:|---:|---:|---:|
'''
for x in summary:
    if x['median_paired_qps_change_percent'] is None:
        section += f'| {x["operation"]} | {x["connections"]} | 包含错误，见原始数据 | — | — | — |\n'
    else:
        lo, hi = x['qps_change_range_percent']; plo, phi = x['p99_change_range_percent']
        section += f'| {x["operation"]} | {x["connections"]} | {x["median_paired_qps_change_percent"]:+.2f}% | {lo:+.2f}% 至 {hi:+.2f}% | {x["median_paired_p99_change_percent"]:+.2f}% | {plo:+.2f}% 至 {phi:+.2f}% |\n'
section += '\n'
p = D / 'README.md';s = p.read_text();assert '## 三轮大数据写入控制复测' not in s
s = s.replace('## 与三库历史对照的剩余差距\n', section + '## 与三库历史对照的剩余差距\n')
s = s.replace('100 MiB 写入控制仍待完成。', '100 MiB 写入控制已完成，结果另列于下方。')
s = s.replace('100 MiB 写入控制仍在运行。', '100 MiB 写入控制已完成，结果另列于下方。')
s = s.replace('100 MiB 独立写入控制尚未完成。', '100 MiB 独立写入控制也已完成，结果另列于下方。')
p.write_text(s);files.append(p)
relative = [str(p.relative_to(repo)) for p in files]
subprocess.run(['/tmp/lavik-precommit-env/bin/pre-commit', 'run', '--files', *relative], cwd=repo, check=True)
subprocess.run(['git', 'add', '--', *relative], cwd=repo, check=True)
subprocess.run(['git', 'diff', '--cached', '--check'], cwd=repo, check=True)
subprocess.run(['git', 'commit', '-m', 'bench: publish paired large Stream write controls'], cwd=repo, check=True)
subprocess.run(['git', 'push', 'https://github.com/thweetkomputer/lavik', 'HEAD:refs/heads/bench/complex-structures-2026-09-26'], cwd=repo, check=True)
print('LARGE_STREAM_WRITE_CONTROLS_PUBLISHED')
