"""Write the merged-main report from audited measurements, preserving scope."""
from pathlib import Path
import csv
import importlib.util
import json
import shutil
import statistics

W = Path(__file__).parent
R = Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26')
D = R / 'diagnostics/main-c55e52c9-20261008'
read = lambda p: json.loads(p.read_text())
m = read(R / 'current-main.json')
v = read(W / 'versions.json')['main']
g = read(D / 'main-gap-summary.json')
mixed = read(R / 'current-mixed-writes.json')
audit = read(D / 'mixed-command-audit.json')
assert m['target_main'] == mixed['target_main'] == v['commit'] == 'c55e52c98d785dec9603d33ddcf55eab299eb11e'
guard_failures = audit['guard_failures']
passed_mixed = audit['selected_passed_points']
assert passed_mixed + len(guard_failures) == 160
assert g['conditions'] == 28 and g['points'] == 278 and audit['points'] == 200

old = read(R / 'diagnostics/main-920f879b-20261006/main-gap-summary.json')
old_points = {(p['condition'], p['command'], p['connections']): p for p in old['points_detail']}
changes = []
for p in g['points_detail']:
    previous = old_points[p['condition'], p['command'], p['connections']]
    c = {k: p[k] for k in ['condition', 'command', 'connections']}
    c.update(previous_qps=previous['main_qps'], current_qps=p['main_qps'],
             previous_p99_ms=previous['main_p99_ms'], current_p99_ms=p['main_p99_ms'],
             previous_error=previous['main_error'], current_error=p['main_error'])
    ok = not p['main_error'] and not previous['main_error']
    c['qps_change_percent'] = (p['main_qps'] / previous['main_qps'] - 1) * 100 if ok else None
    c['p99_change_percent'] = (p['main_p99_ms'] / previous['main_p99_ms'] - 1) * 100 if ok else None
    changes.append(c)
(D / 'previous-main-comparison.json').write_text(json.dumps({
    'previous_main': old['main_commit'], 'current_main': m['target_main'],
    'method': 'Independent single scans, not paired repeated measurements. Layout and process seeds can vary. No individual-PR causal claim.',
    'points': changes}, indent=2) + '\n')
lines = ['# 与上一轮 main 的观测对比', '',
         '相同网格的 `920f879b` 与 `c55e52c9` 独立单次扫描；不是同期交替配对。进程种子、布局和后台工作可能不同，不能将变化直接归因于 #288 或其他单一提交。失败保留；仅在两边成功时计算比例。', '',
         '| 命令 | 可比点数 | QPS 变化中位 | QPS 变化范围 | p99 变化中位 |',
         '|---|---:|---:|---:|---:|']
for op in sorted({p['command'] for p in changes}):
    q = [p['qps_change_percent'] for p in changes if p['command'] == op and p['qps_change_percent'] is not None]
    t = [p['p99_change_percent'] for p in changes if p['command'] == op and p['p99_change_percent'] is not None]
    if q:
        lines.append(f'| {op} | {len(q)} | {statistics.median(q):+.2f}% | {min(q):+.2f}%–{max(q):+.2f}% | {statistics.median(t):+.2f}% |')
lines += ['', '[完整逐点结果](previous-main-comparison.json)。这是逐点变化的无权重中位数，不是总 QPS 变化。p99 负值表示改善。', '']
(D / 'previous-main-comparison.md').write_text('\n'.join(lines))

data = read(W / 'mixed-results.json')
by = {(x['result']['logical_bytes'], x['result']['operation'], x['system'], x['result']['connections']): x['result'] for x in data}
lines = ['# List / ZSet 随机增删：四库对照', '',
         '[主报告](../../README.zh-CN.md) · [全部图与源数据](../../current-mixed-writes.json) · [逐请求计数及逐 key 长度核验](mixed-command-audit.json)', '',
         '本轮四库均重新运行：Lavik main `c55e52c9`，Redis 8.8.0、Valkey 9.1.0，Kvrocks 2.16.0（RocksDB 11.1.1，与原报告同一二进制）。各点的 INFO SERVER、二进制 SHA、启动参数、Kvrocks 有效配置和源提交在 raw 目录。', '',
         '8 个 key，每 key 初始 value/member 逻辑字节为 8 MiB 或 100 MiB，元素 1 KiB。每请求独立均匀选 key，再独立以 50% 概率增或删；每点 30 秒，连接数 80/320/1280/2560，16 客户端线程，pipeline=1。客户端随机种子为 42；每点使用同一客户端二进制并核验 SHA。客户端运行在独立 172.16.0.5，固定 CPU 0–15。', '',
         'List 对比 LPUSH/RPOP 与 RPUSH/LPOP。ZSet 使用唯一新成员的 ZADD NX，分别与 ZPOPMAX 或 ZPOPMIN 混合：头插分数持续降低，尾插分数持续升高，随机插入在原始分数区间均匀选分数。低分和高分方向按客户端发号分别递减或递增，分数始终低于或高于初始区间；多个连接在服务端的到达顺序可能重排，因此不保证每次都是绝对首位或末位插入。淘汰后随机分数也不代表均匀插入排名。所有 ZADD 必须实际插入，所有 pop 必须非空，计数、响应长度和每个 key 的净变化均核验。', '',
         '每点单独启动服务并重新预填；Lavik 重新准备授权 scratch 介质，Kvrocks 使用新的数据库目录，避免仅 FLUSHALL 遗留 LSM 工作。List 用 RPUSH 预填，ZSet 按递增分数预填。Lavik 等待事务清理稳定；Kvrocks 等待两次间隔 2 秒的 flush/compaction 空闲快照；Redis/Valkey 预填后空闲 2 秒。预填和等待不计入 QPS。', '',
         'Lavik 使用与之前 Fenwick 对照相同的固定启动 digest seed，并从进程内存核验；shim 仅在 main 前初始化种子，不挂请求路径，不改动生产二进制。其他系统保留自身内部路由。不同系统的相同逻辑请求不意味着内部物理布局相同。', '',
         'Redis/Valkey 关闭持久化、12 个 I/O 线程；Kvrocks 使用 16 worker、同组六块 NVMe 的无压缩 RAID0，WAL 关闭、80 GiB block/blob cache；Lavik 12 worker、SPDK 持久化、8 GiB EAL，不缓存字段或页内容。主机总预算均为 16 vCPU；写入排名不代表相同持久性保证。', '',
         '这是一次完整并发扫描，没有重复样本或置信区间。图中 QPS 统计命令数而非增删对数，p99 为混合请求分布；每个命令各自的 p99 也保存在 client/result JSON。时间驱动负载中吞吐不同会导致周转次数不同；等概率只约束期望，不保证无限期大小有界。', '',
         f"已核对当前选定的 {audit['selected_points']} 点、{audit['selected_requests']:,} 条命令，INFO commandstats 与客户端计数完全一致；最终长度全部等于初始长度 + 实际增 - 实际删。", '']
for size in [8388608, 104857600]:
    selected = [x for x in audit['checks'] if x['size'] == size and x['guard_passed'] and x['connections'] != 5120]
    lines.append(f"- {size//1048576} MiB/key：纳入曲线点的最大最终长度偏差 {max(x['max_abs_final_change_pct'] for x in selected):.2f}%。")
lines += ['', f'当前选定网格共 {passed_mixed}/160 点满足预设长度范围并纳入曲线；{len(guard_failures)} 点触发范围检查，保留原始数据并在图中留空，没有挑选重跑。', '']
for failure in guard_failures:
    f = failure['failure']
    lines.append(f"- {failure['system']} / {failure['operation']} / {failure['size']//1048576} MiB / c{failure['connections']}：初始 {f['initial_per_key']}，最终最小 {min(f['final_counts'].values())}、最大 {max(f['final_counts'].values())}，预设范围 [{f['minimum']}, {f['maximum']}]。客户端和服务器没有命令错误；[原始记录](../../{failure['raw']}/workload-guard.json)。")
lines += ['', '正式测量的客户端、预填、随机序列与时长未改。第一次长度边界失败后，仅修改执行器以保留这种已完成测量且正常停服的失败，并继续后续点；其余错误仍停止执行。两版执行器、原始失败日志及 SHA 均保留。', '']
lines += ['', '连接档位已按用户要求去掉 5120。新增负载此前测完 200 点，其中 40 点只保留在原始存档，不进入当前曲线、汇总或长度偏差统计；当前图表选择 160 点。旧网格已测出的 5120 也只存档，后续扫描已跳过该档。见 [档位调整记录](connection-policy-change.json)。', '', '## c320 截面', '',
          '只是同一张并发图的 c320 截面，不从不同并发挑各系统最好值。完整曲线同时展示尾延迟。', '',
          '| MiB/key | 操作 | Redis QPS | Valkey QPS | Kvrocks QPS | Lavik QPS | Lavik / 最快 peer |',
          '|---|---|---:|---:|---:|---:|---:|']
for chart in mixed['charts']:
    size, op = chart['size'], chart['operation']
    values = [by[size, op, system, 320]['qps'] for system in ['redis', 'valkey', 'kvrocks', 'lavik']]
    lines.append(f'| {size//1048576} | {op} | ' + ' | '.join('guard fail' if x is None else f'{x:,.0f}' for x in values) + (' | — |' if any(x is None for x in values) else f' | {values[-1]/max(values[:3]):.1%} |'))
lines += ['', '| MiB/key | 操作 | Redis p99 ms | Valkey p99 ms | Kvrocks p99 ms | Lavik p99 ms |',
          '|---|---|---:|---:|---:|---:|']
for chart in mixed['charts']:
    size, op = chart['size'], chart['operation']
    values = [by[size, op, system, 320]['p99_ms'] for system in ['redis', 'valkey', 'kvrocks', 'lavik']]
    lines.append(f'| {size//1048576} | {op} | ' + ' | '.join('guard fail' if x is None else f'{x:,.3f}' for x in values) + ' |')
lines += ['', '## 方法范围', '',
          '当前 List 的满首页 LPUSH 会触发左侧装满的分裂，后续目录序号变化仍需目录重建；Fenwick 主要降低页拓扑不变时的计数更新成本。此处是当前 main 的跨系统实测，不把早先 `78c43ad9` 对 cumulative 的三轮变化比例作为本轮成绩。', '',
          '[连接档位调整](connection-policy-change.json) · [客户端](random-client.cpp) · [混合运行器](run-random.py) · [执行顺序](run-mixed-suite.py) · [完整协议](protocol.json) · [20 个协议检查点](mixed-smoke-results.json)。短时兼容性检查不纳入图表。', '']
(D / 'mixed-writes.md').write_text('\n'.join(lines))

failed = [p for p in g['points_detail'] if p['main_error']]
lines = ['# 合并后 main `c55e52c9` 与四库随机增删', '',
         f"固定 main `{v['commit']}`，包含 #286、#287、#288。原有 28 组命令网格选定 278 点：{278-len(failed)} 成功、{len(failed)} 失败；另外 4 组批量 HSET/SADD 导入完成。新增随机增删四库选定 160 点：{passed_mixed} 点纳入曲线、{len(guard_failures)} 点因长度范围检查留空，生成 10 张 QPS/p99 图。", '',
         '[主报告](../../README.zh-CN.md) · [新增随机增删](mixed-writes.md) · [原有命令与三库差距](main-gap-summary.md) · [与上一轮 main 的观测对比](previous-main-comparison.md) · [构建与硬件](host-and-build.json) · [命令核验](main-command-audit.json) · [混合写核验](mixed-command-audit.json) · [绘图核验](report-audit.json)', '',
         '原有图沿用此前协议：每点 8 秒，扩展 key 数 LSET 为 10 秒，pipeline=1，278 个选定测点和四组批量导入重新测量 Lavik；其他三库保留明确的历史源数据。新增图四库均重新测量、每点 30 秒；两种数据集不拼接为同一曲线。每次测量独占同一测试主机，构建与功能验证先完成；未在本轮吞吐窗口挂 perf。', '',
         '原有 List/Stream/ZSet 覆盖 64 KiB、1 MiB、100 MiB/key 和 128/1024 B 元素；Hash/Set 及扩展 LSET 使用 1 MiB/50,000 keys、100 MiB/500 keys。新随机增删使用 8 MiB/8 keys、100 MiB/8 keys、1 KiB 元素。数据规模、key 数、协议、存储配置和来源均在图标题、manifest 和 raw 中保留。', '',
         '两次旧命令扫描不是同期配对实验，Hash/Set 的进程 digest seed 与布局可能不同，不把主分支整体变化直接解释成 #288 的收益。此前 Fenwick 消融测量仍只代表其固定实测提交。', '',
         '## 功能验证', '']
for name, t in v['tests'].items():
    skipped = sum(case.get('result') == 'SKIPPED' for suite in t['testsuites'] for case in suite['testsuite'])
    lines.append(f"- `{name}`：{t['tests']-t['failures']-skipped} 通过，{skipped} 跳过，{t['failures']} 失败。")
lines += ['', '故障注入用例按生产构建配置跳过，不记作已执行。首次命令级验证被临时目录包装脚本中残留的旧路径白名单拦住，尚未启动测试；修正为本任务私有目录后，复用已核验 SHA 的二进制完成全部测试。初次启动失败日志保留，未伪装成数据库测试通过。', '',
          '## 失败与收尾', '', '20 个短时协议检查完成后、正式测点启动前，一次磁盘空闲检查遇到临时设备占用并拒绝继续。等待两次间隔 2 秒的空闲快照后通过原有检查，再开始正式测量；未跳过保护检查，未覆盖正式结果。原始启动日志保留。', '']
if failed:
    lines += ['原有命令的以下失败保留在 CSV、图中空缺和 raw 错误中，不记为零 QPS，也不删除挑选重跑值：', '']
    lines += [f"- {p['condition']} / {p['command']} / c{p['connections']}。" for p in failed]
else:
    lines += ['原有 278 个选定点均成功，所有服务正常退出。']
lines += ['', '四库 200 次测量全部落盘后，Kvrocks RAID 已拆除，但收尾设备空闲检查又出现一次短暂占用。通过原有幂等恢复流程重试，并取得两次空闲快照后继续旧网格；没有重跑混合测点。见 [恢复记录](mixed-cleanup-retry.json)。', '', '六块授权测试 NVMe 已恢复内核驱动；测试服务停止、Kvrocks RAID 拆除，SPDK hugepages 和 no-IOMMU 设置恢复。见 [主机核验](host-final.json)。原工作区已有的 `perf_reports/README.md` 修改未动；主机运行状态文件不随报告提交。', '',
          '[执行器](refresh-main.py) · [原有网格](run-condition.py) · [批量导入](run-import.py) · [新增混合写](run-mixed-suite.py) · [构建验证](validate-native.py) · [协议](protocol.json) · [完成日志](main-refresh-driver.log) · [证据索引](main-evidence-index.json)。运行脚本保留实际机器、二进制和磁盘白名单路径；移机需配置相应环境。', '']
(D / 'README.md').write_text('\n'.join(lines))
m['notes'] = {'zh': '[本轮测量与验证](diagnostics/main-c55e52c9-20261008/README.md) · [新增四库随机增删](diagnostics/main-c55e52c9-20261008/mixed-writes.md) · [与上一轮 main 的观测对比](diagnostics/main-c55e52c9-20261008/previous-main-comparison.md)。#288 已合并，当前 Lavik 曲线均来自合并后的 main；历史 PR 结果保留原始实测提交。',
              'en': '[Measurements and validation](diagnostics/main-c55e52c9-20261008/README.md) · [Fresh four-system random add/pop](diagnostics/main-c55e52c9-20261008/mixed-writes.md) · [Comparison with the previous main](diagnostics/main-c55e52c9-20261008/previous-main-comparison.md). #288 is merged. All current Lavik curves measure the merged main; historical PR evidence retains its measured revisions.'}
(R / 'current-main.json').write_text(json.dumps(m, indent=2) + '\n')
spec = importlib.util.spec_from_file_location('plot', R / 'plot_current_main.py')
plot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plot)
for zh, name in [(True, 'README.zh-CN.md'), (False, 'README.md')]:
    (R / name).write_text(plot.readme(m, zh))
print('BILINGUAL_REPORT_WRITTEN', len(failed), 'retained legacy failures')
