"""Publish completed paired reads without staging mutable benchmark host files."""
from pathlib import Path
import json
import shutil
import statistics
import subprocess

W = Path(__file__).parent
repo = Path('/mnt/dev/lavik-complex-refresh-20261004')
R = repo / 'perf_reports/lavik-complex-structures-2026-09-26'
D = R / 'diagnostics/stream-reply-20261004'
assert 'ALL_STREAM_REPLY_READ_REPEATS_COMPLETE' in (W / 'stream-reply-read-repeat-driver.log').read_text()
v = json.loads((W / 'stream-reply-read-repeats.json').read_text())
assert len(v['rows']) == 24 and len(v['seeds']) == 3
summaries = []
for op, c in [('XRANGE_FULL', 1), ('XRANGE_FULL', 4), ('XRANGE_FULL', 16), ('XRANGE', 2560)]:
    pairs = []
    for n in (1, 2, 3):
        pair = {x['version']: x for x in v['rows'] if (x['round'], x['operation'], x['connections']) == (n, op, c)}
        assert set(pair) == {'main', 'candidate'}
        a, b = pair['main'], pair['candidate']
        failed = 'error' in a or 'error' in b
        pairs.append({'round': n, **pair,
                      'qps_change_percent': None if failed else 100 * (b['qps'] / a['qps'] - 1),
                      'p99_change_percent': None if failed else 100 * (b['p99_ms'] / a['p99_ms'] - 1)})
    gains = [p['qps_change_percent'] for p in pairs if p['qps_change_percent'] is not None]
    tails = [p['p99_change_percent'] for p in pairs if p['p99_change_percent'] is not None]
    summaries.append({'operation': op, 'connections': c, 'pairs': pairs,
                      'median_paired_qps_change_percent': statistics.median(gains) if len(gains) == 3 else None,
                      'qps_change_range_percent': [min(gains), max(gains)] if gains else None,
                      'median_paired_p99_change_percent': statistics.median(tails) if len(tails) == 3 else None})
result = {'main': v['main'], 'candidate': v['candidate'], 'method': v['method'], 'rows': summaries,
          'limitations': '30-second command windows; large full-range points have few completed requests and rounded QPS, limiting precision and especially tail-latency inference. Read-only same-population pairs differ from initial post-XADD sweeps. Not a measurement of current merged PR heads or evidence of peer parity. Write and small-read controls are separate.'}
(D / 'stream-reply-read-repeat-summary.json').write_text(json.dumps(result, indent=2) + '\n')
files = [D / 'stream-reply-read-repeat-summary.json']
for name in ['stream-reply-read-repeats.json', 'repeat-stream-reply-reads.py', 'run-stream-reply-reads.py',
             'repeat-stream-reply-controls.py', 'publish-stream-reply-read-repeats.py']:
    target = D / name
    shutil.copyfile(W / name, target)
    files.append(target)
tags = {x['tag'] for x in v['rows']} | {x['tag'] for x in v['seeds']}
for tag in sorted(tags):
    raw = R / 'raw' / ('lavik-' + tag)
    assert json.loads((raw / 'server-exit.json').read_text())['code'] == 0
    assert (raw / 'complete.json').exists()
    files.extend(raw.glob('*.json'))
section = '''## 三轮同一数据集读取复测

每轮由 main 新建数据，干净退出后两个固定二进制分别恢复同一未修改的数据集；交替 A/B、B/A、A/B，每点 30 秒。所有前后基数均核对，测量期间没有构建、测试或 perf。这里只复测 100 MiB / 128 B / 8 keys；和初测经过 XADD 后的 population 不同，不能混合为一组重复样本。

[全部 24 个观测及源码/二进制出处](stream-reply-read-repeats.json) · [逐对变化与汇总](stream-reply-read-repeat-summary.json) · [复测脚本](repeat-stream-reply-reads.py)。表中为逐对变化的中位数，并保留三轮范围。全量命令请求数少且 QPS 已取整到两位小数，尾延迟精度有限。

| 命令 | 并发 | QPS 变化中位数 | 三轮 QPS 变化范围 | p99 变化中位数 |
|---|---:|---:|---:|---:|
'''
for x in summaries:
    if x['median_paired_qps_change_percent'] is None:
        section += f'| {x["operation"]} | {x["connections"]} | 包含错误，见原始数据 | — | — |\n'
    else:
        lo, hi = x['qps_change_range_percent']
        section += f'| {x["operation"]} | {x["connections"]} | {x["median_paired_qps_change_percent"]:+.2f}% | {lo:+.2f}% 至 {hi:+.2f}% | {x["median_paired_p99_change_percent"]:+.2f}% |\n'
section += '\n配对结果不能替代写入和小数据控制；这些另行复测。单条回复消除额外缓冲区的 [Draft PR #274](https://github.com/eloqdata/lavik/pull/274) 尚无性能结果。所有本节数据仍属于 `1e87107e`，并非 PR #270 合入新 main 后的提交或 #274。\n\n'
p = D / 'README.md'
s = p.read_text()
assert '## 三轮同一数据集读取复测' not in s
s = s.replace('## 需要复测的退化点\n', section + '## 需要复测的退化点\n')
s = s.replace('全部 XRANGE、XADD MAXLEN 控制点及错误均在链接数据中；仍需交替复测。', '全部 XRANGE、XADD MAXLEN 控制点及错误均在链接数据中；三轮大数据读取复测另列于下方，写入及小数据控制仍待完成。')
s = s.replace('PR 保持草稿，配对读取和独立写入控制复测尚未完成。', 'PR 保持草稿；大数据配对读取已完成，独立写入与小数据控制复测尚未完成。')
s = s.replace('故障专用和可选 RDB 跳过项保留，完整故障覆盖来自 CI。', '14 项 Stream 测试通过（含大 RDB 往返），仅 1 项故障专用测试跳过；完整故障覆盖来自 CI。')
p.write_text(s)
files.append(p)
relative = [str(p.relative_to(repo)) for p in files]
subprocess.run(['/tmp/lavik-precommit-env/bin/pre-commit', 'run', '--files', *relative], cwd=repo, check=True)
subprocess.run(['git', 'add', '--', *relative], cwd=repo, check=True)
subprocess.run(['git', 'diff', '--cached', '--check'], cwd=repo, check=True)
subprocess.run(['git', 'commit', '-m', 'bench: publish three paired Stream read repetitions'], cwd=repo, check=True)
subprocess.run(['git', 'push', 'https://github.com/thweetkomputer/lavik', 'HEAD:refs/heads/bench/complex-structures-2026-09-26'], cwd=repo, check=True)
print(json.dumps(summaries, indent=2))
