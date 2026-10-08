"""Publish only complete audited observations into the existing report checkout."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess

W = Path(__file__).resolve().parent
P = Path('/mnt/dev/lavik-report-c55e52c9-20261008')
R = P / 'perf_reports/lavik-complex-structures-2026-09-26'
D = R / 'diagnostics/pr291-main-1dd8a5b3-20261008'
subprocess.run(['python3', str(W / 'analyze.py'), '--complete'], check=True)
read = lambda p: json.loads(p.read_text())
analysis = read(W / 'analysis.json')
rows = read(W / 'pairs.json')
assert analysis['complete'] and len(rows) == 42
assert read(W / 'host-restored.json')['passed']
D.mkdir(parents=True, exist_ok=True)

names = ['analysis.json', 'summary.csv', 'observations.csv', 'pairs.json',
         'versions.json', 'integration-proof.json', 'main-to-pr291.patch', 'protocol.json', 'host-and-toolchain.json',
         'host-restored.json', 'harness-provenance.json', 'harness-provenance-v1.json',
         'harness-audit-correction.json', 'client-provenance.json',
         'mock-client-validation.json', 'main-CMakeCache.txt', 'pr291-CMakeCache.txt',
         'main-unit.json', 'pr291-unit.json', 'pr291-ordered.json', 'pr291-hash.json',
         'random-client.cpp', 'fixed-digest-seed.c', 'build.py', 'client-build.py',
         'mock-client.py', 'start.py', 'pairs.py', 'analyze.py', 'write-report.py', 'check-restored.py',
         'benchmark.py', 'run-random.py', 'run-random.audit-v1.py', 'host.py',
         'private-tmp-exec.py', 'fixed-seed-exec.py', 'process_helpers.py',
         'profile_capture.py', 'commands.jsonl', 'build-driver.log',
         'client-build.log', 'pairs-driver.log']
names += [x.name for x in W.glob('main-*.log')]
names += [x.name for x in W.glob('pr291-*.log')]
for name in set(names):
    shutil.copy2(W / name, D / name)
support = D / 'runtime-support'
support.mkdir(exist_ok=True)
runtime = Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26')
for name in ('run.py', 'spdk_host.py', 'run_with_memory_guard.py'):
    shutil.copy2(runtime / name, support / name)
shutil.copy2('/mnt/dev/lavik-complex-iterations-20261004/host_execution_lock.py', support)
for row in rows:
    raw = Path(row['raw'])
    shutil.copytree(raw, R / 'raw' / raw.name, dirs_exist_ok=True)
    shutil.copy2(W / (row['tag'] + '.log'), D)

labels = {'LPUSH_RPOP': 'LPUSH / RPOP', 'RPUSH_LPOP': 'RPUSH / LPOP',
          'LSET_RESIZE': 'LSET（1008/1024 B）', 'ZINCRBY': 'ZINCRBY',
          'ZADD_MIDDLE_ZPOPMIN': '随机分数 ZADD / ZPOPMIN',
          'HSET': 'HSET（替换已有字段）', 'SADD_SREM': 'SADD / SREM'}
by_op = {s['operation']: s for s in analysis['results']}
outcome = (f"本次主要吞吐收益为 RPUSH/LPOP **{by_op['RPUSH_LPOP']['qps_change_pct']:+.1f}%**、"
           f"变长 LSET **{by_op['LSET_RESIZE']['qps_change_pct']:+.1f}%** 和 "
           f"HSET **{by_op['HSET']['qps_change_pct']:+.1f}%**，取三轮配对增幅中位数。"
           "前两项的 p99 同时明显上升。HSET 三轮为 +5.1%、+6.9%、-1.2%，尚不是每轮稳定收益。"
           "其余测量只出现小幅 QPS 变化，完整范围见表；"
           "这些结果只适用于下述 8 MiB/key、320 连接负载。")
lines = ['# PR #291 扩展优化：与 main 1dd8a5b3 的 QPS 对照', '',
         '比较 [PR #291](https://github.com/eloqdata/lavik/pull/291) 的完整两笔改动与已合并 #290 的 main。所有结果均为本次重新测量，未复用早期 push/pop 单独优化的结果。', '',
         outcome, '',
         '## 测量范围', '',
         '- main：`1dd8a5b35aefc9215e0090204a0680efe9848e4a`。',
         '- 候选：在上述 main 上顺序应用 PR 的 `309e2af3`、`79bdbfeda`，得到 `74ba1d1ea3af697666b7eeaa06908dd4572eff95`。PR 原始 head 仍为 `79bdbfeda`；此处专门排除 main 新增 #290 的干扰。集成分支为 [`bench/pr291-main-1dd8a5b3-20261008`](https://github.com/thweetkomputer/lavik/tree/bench/pr291-main-1dd8a5b3-20261008)。',
         '- 每个 key 初始 8192 个 1 KiB 元素/值，名义 8 MiB，共 8 个 key。Hash 字段和编码有额外空间；LSET 更新后值长为 1008 或 1024 B。320 连接、16 个客户端线程、pipeline 1，每点 30 秒。QPS 是完成的命令数/客户端实际运行时间，混合操作不按一对命令计数。',
         '- 七项负载各三组配对，共 42 个观测。版本顺序为 main→候选、候选→main、main→候选。同轮同操作的两边使用相同进程 digest seed 和客户端随机种子，跨轮更换种子。固定种子的 shim 仅在进入 main 前初始化种子，不挂请求路径；运行时读进程内存核对种子。',
         '- 每点重新启动服务、清空允许使用的六块独立 scratch NVMe、重新填充并等待提交队列和 cleaner 空闲。继承既有基准的 settle 判据：间隔两秒的两次检查均满足队列为空、cleaner 不运行、总 backlog ≤16 MiB。各点残留 backlog 保存在 observations.csv，不假设全部为零。',
         '- 服务端 12 workers，CPU 0–15，kernel TCP + SPDK；关闭 defrag 和定时 Tomb Raider，其他参数见原始 server-command.json。两边 CMake cache 完全相同：RelWithDebInfo、`-O2 -g -DNDEBUG`、`-march=native`、BUILD_TESTING=OFF、LAVIK_ENABLE_TEST_FAULTS=OFF，Bycorf 与依赖相同。',
         '- 不含 5120 连接，不替换现有四系统全量并发曲线。本次没有 perf 采样；结果是端到端固定连接闭环测量。', '',
         '## 结果', '',
         '绝对值列分别取三轮中位数；增幅列取三个 **候选/main 配对比值的中位数**，因此增幅不必等于两列中位数之比。p99 是每次运行的 p99 再做同样聚合，没有合并各轮延迟样本。', '',
         '|操作|main QPS|候选 QPS|配对 QPS 变化|三轮增幅范围|main p99 ms|候选 p99 ms|配对 p99 变化|',
         '|---|---:|---:|---:|---:|---:|---:|---:|']
for s in analysis['results']:
    lines.append(f"|{labels[s['operation']]}|{s['main_qps']:,.0f}|{s['pr291_qps']:,.0f}|{s['qps_change_pct']:+.1f}%|{s['qps_change_min_pct']:+.1f}% 至 {s['qps_change_max_pct']:+.1f}%|{s['main_p99_ms']:.2f}|{s['pr291_p99_ms']:.2f}|{s['p99_change_pct']:+.1f}%|")
lines += ['', '## 负载语义与边界', '',
          '- List push/pop：每条命令独立均匀选 key，再独立以 50/50 概率选 push 或 pop；两种方向分开测。每次 push 返回长度检查 [4096,16384]，每次 pop 必须非空且 1024 B；最终逐 key 校验初值 + push − pop。',
          '- LSET：每条命令随机选 key，再从八个分散位置选一处，写入唯一内容。不同连接分别写 1008/1024 B，产生长短变化；并非每一条命令都保证长度变化。',
          '- ZINCRBY：随机 key、八个已有成员之一，每次加 1，保证实际改变分数；持续更新会改变分数分布和所在页，因此不是静态布局的查找微基准。',
          '- ZADD/ZPOPMIN：独立随机 key、50/50 操作；ZADD NX 使用唯一 1 KiB member，分数均匀抽取初始分数范围，ZPOPMIN 每次删一个。最终逐 key 检查初值 + 成功新增 − pop。运行中分数分布会变化，不能把全部 ZADD 描述为当前集合的中间插入。',
          '- HSET：随机 key、八个分散的已有字段之一，每次换成唯一 1 KiB 值；HSET 返回 0 表示没有新增字段，不表示值没有变化。此点不覆盖新字段插入、HSETNX 或 HDEL。',
          '- Set：独立随机 key 和 50/50 SADD/SREM，从 16384 个成员的固定池均匀选一个，初始存在 8192 个。返回 0 的空操作保留在 QPS 中，返回 1 才计入实际增删；用真实返回值校验最终数量。', '',
          '|Set 轮次|版本|真正增删占请求比例|最终每 key 数量范围|',
          '|---:|---|---:|---:|']
import csv
with (W / 'observations.csv').open() as f:
    observations = list(csv.DictReader(f))
for o in observations:
    if o['operation'] == 'SADD_SREM':
        lines.append(f"|{o['round']}|{o['version']}|{float(o['set_changed_fraction'])*100:.2f}%|{o['final_cardinality_min']}–{o['final_cardinality_max']}|")
lines += ['', '## 逐轮数据', '',
          '|操作|轮次|main QPS|候选 QPS|QPS 变化|main p99 ms|候选 p99 ms|p99 变化|',
          '|---|---:|---:|---:|---:|---:|---:|---:|']
for s in analysis['results']:
    for p in s['paired_results']:
        lines.append(f"|{labels[s['operation']]}|{p['round']}|{p['main_qps']:,.0f}|{p['pr291_qps']:,.0f}|{p['qps_change_pct']:+.1f}%|{p['main_p99_ms']:.2f}|{p['pr291_p99_ms']:.2f}|{p['p99_change_pct']:+.1f}%|")
lines += ['', '## 验证与解读', '',
          '42 个观测均检查客户端响应、客户端/服务端命令计数、操作比例、最终逐 key 基数、允许范围、二进制 SHA256、种子及正常退出。新增客户端先对独立模拟 RESP 服务检查四项新操作的请求语义、计数和返回值处理；该检查不计入性能数据。', '',
          '同一 main 集成后的普通构建：main 281 项相关单元测试通过；候选 282 项单元测试、4 项有序集合/冷恢复用例和 10 项 Hash 集成用例通过，10 项需要故障注入的 Hash 用例因关闭注入而跳过。PR 原分支的完整故障注入验证另见 PR 描述，不与本次计数混加。', '',
          '三组配对仍是有限样本。表中范围暴露波动；不能仅据中位数断言小幅变化是稳定收益。只测试 8 MiB/key、320 连接，以及以上指定操作；没有覆盖全范围 LTRIM、LINSERT、HSETNX/HDEL、ZREM/ZPOPMAX 或其他并发。固定连接负载在吞吐提高时也增加请求速率，p99 的变化不能单凭此实验归因于吞吐提高；尚无相同 QPS 的延迟对照。新增实现的减少读取/分配意图与端到端 QPS 收益需要分开判断。', '',
          '测试中仅修正一次测量后的审计条件：按实际命令种类数判断是否为混合操作，避免把带下划线的单命令标签 LSET_RESIZE 误判。修正发生于首组 LPUSH/RPOP 的候选点准备阶段，基线已完成；未改变负载、种子或测量，LPUSH/RPOP 的新旧检查等价。两版脚本及 SHA 均保留于 harness-audit-correction.json 与 harness-provenance-v1.json。', '',
          '测试结束已检查六块设备恢复 nvme 驱动、hugepages 和 VFIO no-IOMMU 设置恢复、无遗留服务器，详见 host-restored.json。', '',
          '[完整分析 JSON](analysis.json) · [摘要 CSV](summary.csv) · [逐点 CSV](observations.csv) · [版本/二进制](versions.json) · [测量协议](protocol.json) · [宿主与工具链](host-and-toolchain.json) · [校验脚本](analyze.py) · [文件校验清单](artifact-manifest.json)', '',
          '脚本保留实测时的绝对路径和专用设备允许清单，复现时应先映射工作目录并审查设备清单，不可直接照搬设备操作到其他主机。', '',
          '## 原始数据索引', '', '|操作|轮次|版本|结果|客户端|运行来源|', '|---|---:|---|---|---|---|']
for row in rows:
    raw = Path(row['raw'])
    prefix = '../../raw/' + raw.name + '/'
    result = next(raw.glob('*.result.json')).name
    client = next(raw.glob('*.client.json')).name
    proof = next(raw.glob('provenance-*.json')).name
    lines.append(f"|{labels[row['operation']]}|{row['round']}|{row['version']}|[结果]({prefix+result})|[客户端]({prefix+client})|[来源]({prefix+proof})|")
(D / 'README.md').write_text('\n'.join(lines) + '\n')
files = list(D.rglob('*'))
for row in rows:
    files += list((R / 'raw' / Path(row['raw']).name).rglob('*'))
manifest = {str(p.relative_to(R)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(files) if p.is_file() and p.name != 'artifact-manifest.json'}
(D / 'artifact-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(D)
