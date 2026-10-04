"""Publish completed small controls while the independent large pairs continue."""
from pathlib import Path
import json
import shutil
import statistics
import subprocess

W = Path(__file__).parent
repo = Path('/mnt/dev/lavik-complex-refresh-20261004')
R = repo / 'perf_reports/lavik-complex-structures-2026-09-26'
D = R / 'diagnostics/stream-reply-20261004'
v = json.loads((W / 'stream-reply-control-repeats.json').read_text())
rows = [x for x in v['rows'] if x['logical_bytes'] == 65536]
assert len(rows) == 24
small = {'main': v['main'], 'candidate': v['candidate'], 'rows': rows, 'seeds': v['seeds'],
         'method': 'Three 30-second pairs A/B, B/A, A/B for 64KiB/1024B/64keys. Read pairs restart both immutable binaries on the same unmodified main-seeded population (full XRANGE c80, point XRANGE c5120); write pairs use independent fresh seeds (XADD_MAXLEN c2560/c5120). No builds/tests/perf overlap. Large write pairs are still running and not included here.'}
summary = []
for op, c in [('XRANGE_FULL', 80), ('XRANGE', 5120), ('XADD_MAXLEN', 2560), ('XADD_MAXLEN', 5120)]:
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
files = []
for name, value in [('stream-reply-small-control-repeats.json', small),
                    ('stream-reply-small-control-summary.json', {'main': v['main'], 'candidate': v['candidate'], 'rows': summary, 'method': small['method']})]:
    p = D / name
    p.write_text(json.dumps(value, indent=2) + '\n')
    files.append(p)
for name in ['publish-stream-reply-small-controls.py', 'repeat-stream-reply-controls.py']:
    p = D / name
    shutil.copyfile(W / name, p)
    files.append(p)
for tag in sorted({x['tag'] for x in rows} | {x['tag'] for x in small['seeds']}):
    raw = R / 'raw' / ('lavik-' + tag)
    assert json.loads((raw / 'server-exit.json').read_text())['code'] == 0
    assert (raw / 'complete.json').exists()
    files.extend(raw.glob('*.json'))
section = '''## 三轮小数据控制复测

64 KiB / 1024 B / 64 keys，每点 30 秒，交替 A/B、B/A、A/B。读取复用每轮 main 新建且未修改的数据集；写入为每个版本独立新建数据。全量读取增益稳定，初测的点读退化没有稳定重现；但 XADD 在 5120 并发的 p99 三轮都变差，不能只看近乎不变的 QPS。100 MiB 写入控制仍在运行。

[全部 24 个观测](stream-reply-small-control-repeats.json) · [逐对变化及汇总](stream-reply-small-control-summary.json)。仍使用固定 `a565d603` / `1e87107e` 二进制，并非新 main 或后续 PR 的性能。

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
p = D / 'README.md';s = p.read_text();assert '## 三轮小数据控制复测' not in s
s = s.replace('## 与三库历史对照的剩余差距\n', section + '## 与三库历史对照的剩余差距\n')
s = s.replace('写入及小数据控制仍待完成。', '小数据控制复测已完成，100 MiB 写入控制仍待完成。')
s = s.replace('大数据配对读取已完成，独立写入与小数据控制复测尚未完成。', '大数据配对读取及小数据读写控制已完成，100 MiB 独立写入控制尚未完成。')
s = s.replace('配对结果不能替代写入和小数据控制；这些另行复测。', '配对结果不能替代写入和小数据控制；已完成的小数据读写结果另列于下方，100 MiB 写入控制仍在运行。')
p.write_text(s);files.append(p)
relative = [str(p.relative_to(repo)) for p in files]
subprocess.run(['/tmp/lavik-precommit-env/bin/pre-commit', 'run', '--files', *relative], cwd=repo, check=True)
subprocess.run(['git', 'add', '--', *relative], cwd=repo, check=True)
subprocess.run(['git', 'diff', '--cached', '--check'], cwd=repo, check=True)
subprocess.run(['git', 'commit', '-m', 'bench: publish paired small Stream read and write controls'], cwd=repo, check=True)
subprocess.run(['git', 'push', 'https://github.com/thweetkomputer/lavik', 'HEAD:refs/heads/bench/complex-structures-2026-09-26'], cwd=repo, check=True)
print('SMALL_STREAM_CONTROLS_PUBLISHED')
