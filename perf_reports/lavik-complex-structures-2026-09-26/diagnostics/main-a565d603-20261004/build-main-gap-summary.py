"""Summarize every matched main/peer observation without combining PR heads."""
from pathlib import Path
import csv
import hashlib
import json
import math
import statistics
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[2]
manifest = json.loads((root / 'current-main.json').read_text())
assert all(row['main']['fresh'] for row in manifest['plots']), 'Finish all main grids first'
commit = manifest['target_main']
label = 'Lavik main ' + commit[:8]
points = []
sources = []
for condition in manifest['plots']:
    assert condition['main']['commit'] == commit
    name = f"{condition['kind']}-{condition['size']}-{condition['field']}-k{condition['keys']}"
    path = root / (name + '-current.csv')
    data = list(csv.DictReader(path.open()))
    sources.append({'condition': name, 'csv': path.name,
                    'csv_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                    'main_tag': condition['main']['tag'],
                    'main_binary_sha256': condition['main']['sha256']})
    selected = [row for row in data if row['series'] == label]
    assert selected, (path, label)
    seen = set()
    for row in selected:
        identity = row['command'], int(row['connections'])
        assert identity not in seen
        seen.add(identity)
        peers = [peer for peer in data if peer['series'] in ('Redis', 'Valkey', 'Kvrocks (80 GiB cache)')
                 and (peer['command'], int(peer['connections'])) == identity]
        assert {peer['series'] for peer in peers} == {'Redis', 'Valkey', 'Kvrocks (80 GiB cache)'} and len(peers) == 3
        assert not any(peer['error'] for peer in peers)
        peer_values = {peer['series']: {'qps': float(peer['qps']), 'p99_ms': float(peer['p99_ms'])}
                       for peer in peers}
        assert all(math.isfinite(v['qps']) and v['qps'] > 0 for v in peer_values.values())
        fastest = max(peer_values, key=lambda key: peer_values[key]['qps'])
        qps = None if row['error'] else float(row['qps'])
        if qps is not None: assert math.isfinite(qps) and qps > 0
        points.append({'condition': name, 'command': identity[0], 'connections': identity[1],
                       'main_qps': qps, 'main_p99_ms': None if row['error'] else float(row['p99_ms']),
                       'main_error': row['error'] or None, 'peers': peer_values,
                       'fastest_peer': fastest,
                       'ratio_to_fastest_peer': None if qps is None else qps / peer_values[fastest]['qps']})
summary = []
for command in sorted({p['command'] for p in points}):
    rows = [p for p in points if p['command'] == command]
    ratios = [p['ratio_to_fastest_peer'] for p in rows if p['main_error'] is None]
    summary.append({'command': command, 'points': len(rows), 'successful': len(ratios),
                    'errors': len(rows) - len(ratios),
                    'median_ratio': statistics.median(ratios) if ratios else None,
                    'minimum_ratio': min(ratios) if ratios else None,
                    'maximum_ratio': max(ratios) if ratios else None,
                    'at_least_80pct': sum(r >= .8 for r in ratios),
                    'at_least_fastest': sum(r >= 1 for r in ratios)})
summary.sort(key=lambda row: row['median_ratio'] if row['median_ratio'] is not None else -1)
out = root / Path(manifest['build_proof']).parent
record = {'main_commit': commit, 'conditions': len(manifest['plots']), 'points': len(points),
          'scope': 'All fresh pinned-main observations only; no best-of-PR composition. Historical peers use different persistence/cache settings. Unweighted median of per-point ratios is not aggregate throughput. The 80% band is a provisional triage aid, not a user-agreed acceptance criterion. Errors remain in denominators and are excluded from ratio statistics.',
          'sources': sources, 'summary': summary, 'points_detail': points}
(out / 'main-gap-summary.json').write_text(json.dumps(record, indent=2) + '\n')
lines = [f'# 完整 main 基线差距：`{commit[:8]}`', '',
         f"{len(manifest['plots'])}/{len(manifest['plots'])} 组命令复测，合计 {len(points)} 个 main 测点。批量导入单独计时，不混入此表。",
         '', '[逐点 QPS、p99、错误与 CSV 哈希](main-gap-summary.json) · [复现脚本](build-main-gap-summary.py) · [主报告](../../README.zh-CN.md)', '',
         '每个比值均匹配相同命令、数据大小、元素大小、key 数和连接数，分母为该点 Redis、Valkey、Kvrocks 中最高的历史 QPS。表中的中位数是各测点比值的无权重中位数，不是总吞吐，也不代表每个大小或并发都接近。失败点计入总数；比值统计只用成功点。', '',
         '这里只使用固定 main，不混入未合并 PR，也不从不同 PR 挑选最好测点。其他三库本轮未重跑；Redis/Valkey 关闭持久化，Kvrocks 关闭 WAL 并有 80 GiB cache，Lavik 使用六块 NVMe SPDK 持久化且无字段/页内容缓存。配置差异限制了写入排名的含义。单次扫描没有置信区间。', '',
         '“达到最快 peer 的 80%”仅作暂定排查参考，不是用户确认的验收线，更不是整体达标结论。p99 必须结合逐点记录审查，不能用 QPS 中位数替代。', '',
         '| 命令 | 成功/总测点 | QPS 比值中位数 | 比值范围 | ≥80% 测点 | ≥100% 测点 |',
         '|---|---:|---:|---:|---:|---:|']
for row in summary:
    lines.append(f"| {row['command']} | {row['successful']}/{row['points']} | {row['median_ratio']:.1%} | {row['minimum_ratio']:.1%}–{row['maximum_ratio']:.1%} | {row['at_least_80pct']} | {row['at_least_fastest']} |")
lines += ['', '## 下一步优先级', '',
          'XADD_MAXLEN 和 ZINCRBY 仍是主要差距，应继续检查重复页读取、解码、哈希和写入编码。现有大对象测试的提交队列高水位等待计数没有增长，不能直接归因于队列堵塞；因果提交和恢复顺序必须保留。', '',
          '[Stream 尾部目录复用](../stream-suffix-20261004/README.md)和 [ZSet 成员叶页复用](../zset-member-probe-20261004/README.md)已有独立配对结果，仍未解决整体差距。[Stream 回复合并草稿](../stream-range-main-20261004/README.md)与内联页清单查找草稿的候选性能尚待测量。', '',
          '[List 回复预留与有界读取](../list-reply-reserve-20261004/README.md)解决了已测的大范围读取瓶颈及内存失败；[更宽窗口的配对复测](../list-byte-window-20261004/README.md)仍有高并发尾延迟和写入控制点回退，不能只按低并发收益推广。', '',
          '当前证据不支持宣称复杂数据结构整体已经与另外三个系统处于同一性能水平。', '']
(out / 'main-gap-summary.md').write_text('\n'.join(lines))
print(json.dumps({'conditions': len(manifest['plots']), 'points': len(points), 'summary': summary}, indent=2))
