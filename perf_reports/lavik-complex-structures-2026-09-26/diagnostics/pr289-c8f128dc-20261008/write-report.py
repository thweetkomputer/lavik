"""Write reviewable findings without treating three samples as a confidence bound."""
from pathlib import Path
import json

W = Path(__file__).parent
summary = json.loads((W / 'summary.json').read_text())
audit = json.loads((W / 'command-audit.json').read_text())
versions = json.loads((W / 'versions.json').read_text())
perf = json.loads((W / 'perf-summary.json').read_text())
lines = ['# PR #289：ZRANK 与 List push/pop 对照（2026-10-08）', '',
         '[主报告](../../README.zh-CN.md) · [PR #289](https://github.com/eloqdata/lavik/pull/289) · [逐轮数据](repeats.json) · [汇总 CSV](summary.csv) · [逐点 CSV](observations.csv)', '',
         '**实测版本：main `c55e52c98d785dec9603d33ddcf55eab299eb11e`，PR `c8f128dc5eb1a9d52d1d64f53657e6e3c9215616`。PR 的共同祖先就是这份 main，比较包含该 PR 的全部改动。**', '',
         '两版均重新测量，按 main/PR、PR/main、main/PR 做三轮交替。每点 30 秒、320 连接、16 客户端线程、pipeline=1；8 个 key，每 key 初始 8 MiB 或 100 MiB，元素/成员 1 KiB。测试只覆盖这个并发截面，未测 5120，不将旧扫描与本轮配对数据拼接。', '',
         '每个测点都启动新服务、重新准备同一组六块授权 SPDK NVMe 并预填，再等待事务清理稳定。两版固定相同的生产 CMake 配置、依赖、12 个 worker、16 vCPU 主机预算和 8 GiB EAL。远端客户端在独立机器运行，固定 CPU 0–15。每对使用相同的客户端随机种子和服务端 digest seed，每轮更换种子。', '',
         '## QPS 与 p99', '',
         '绝对 QPS/p99 是各版三轮中位数；变化和倍数是每一对 PR/main 比值的中位数，不能直接用绝对中位数相除替代。QPS 正值、p99 负值表示改善。图中误差线只表示三次观察的最小值到最大值，不是置信区间。', '',
         '| MiB/key | 操作 | main QPS | PR QPS | QPS 倍数 | QPS 变化 | p99 变化 | 三轮 QPS 变化 |',
         '|---|---|---:|---:|---:|---:|---:|---|']
for s in summary:
    changes = ', '.join(f"{p['qps_change_pct']:+.2f}%" for p in s['pairs'])
    lines.append(f"| {s['size']//1048576} | {s['operation']} | {s['main_qps']:,.1f} | {s['pr289_qps']:,.1f} | {s['qps_ratio']:.2f}× | {s['qps_change_pct']:+.2f}% | {s['p99_ms_change_pct']:+.2f}% | {changes} |")
small = next(s for s in summary if s['size'] == 8388608 and s['operation'] == 'RPUSH_LPOP')
lines += ['', f"**小 List 回退需单独看：8 MiB RPUSH/LPOP 的配对 QPS 变化中位数为 {small['qps_change_pct']:+.2f}%，三轮范围 {small['qps_change_range_pct'][0]:+.2f}% 到 {small['qps_change_range_pct'][1]:+.2f}%；p99 变化中位数 {small['p99_ms_change_pct']:+.2f}%。该项波动大，不能把本 PR 描述为所有 List 场景都加速。**", '']
lines += ['', '| MiB/key | 操作 | main p99 ms | PR p99 ms |', '|---|---|---:|---:|']
for s in summary:
    lines.append(f"| {s['size']//1048576} | {s['operation']} | {s['main_p99_ms']:,.3f} | {s['pr289_p99_ms']:,.3f} |")
lines += ['', '![List comparison](list-comparison.png)', '', '![ZSet rank comparison](zset-comparison.png)', '',
          '## 负载含义与适用范围', '',
          '- List 每次请求独立均匀选 key，再独立以 50% 概率选择 LPUSH/RPOP 或 RPUSH/LPOP；没有固定 key、强制配对、Lua 或事务包装。QPS 是命令数，不是增删对数；p99 是两种命令的混合分布。各命令自身的分位数保存在原始 client/result JSON。',
          '- List 使用 RPUSH 预填。每个方向在相同的确定性初始数据上单独开始；等概率增删不保证无限期长度有界。本次核验所有 push 返回值、非空 pop、最终长度和实际增删净变化。',
          '- ZSet 预填分数各不相同且递增。每请求独立均匀选 key，并在从首到尾等距的 8 个排名位置中随机选择目标成员；不是对所有成员均匀取样。ZRANK 和 ZREVRANK 每个回复都与确切排名核对，且测量前后成员数保持不变。',
          '- 本次排名吞吐不覆盖缺失成员、大量同分成员、很小的 compact ZSet、与写命令混合或更高并发。PR 对同分区间仍可能逐页扫描，因此不能将这里的倍数推广到全同分数据。',
          '- 每点按时间结束并排空在途请求。更高吞吐意味着更多次增删周转，可能带来不同最终长度和页历史；这也是实际时间驱动负载的一部分。三对重复提供本轮重复性信息，不构成普遍性能保证。', '',
          '## 正确性与构建检查', '',
          f"- 已独立核验 {audit['points']} 点、{audit['requests']:,} 条命令：客户端计数与服务端 INFO commandstats 一致，无失败/拒绝命令；所有服务正常退出。",
          f"- 插入比例范围 {audit['add_fraction_range'][0]*100:.3f}%–{audit['add_fraction_range'][1]*100:.3f}%；混合写最终长度最大偏差 {audit['max_final_length_deviation_pct']:.2f}%，均在预设 [0.5N, 2N] 范围内。",
          f"- 客户端进程 CPU 使用率 {audit['client_cpu_percent_range'][0]}%–{audit['client_cpu_percent_range'][1]}%（16 核总量为 1600%，包括测量结束后的分位数排序）。",
          '- 两版生产 CMakeCache 字节相同，服务端二进制 SHA 和同一份客户端 SHA 均核验。服务端固定种子使用启动阶段 shim，并读取进程内存确认；没有请求路径 hook，生产二进制不改动。']
for name, t in versions['pr289']['tests'].items():
    skipped = sum(c.get('result') == 'SKIPPED' for suite in t['testsuites'] for c in suite['testsuite'])
    lines.append(f"- PR `{name}`：{t['tests']-t['failures']-skipped} 通过、{skipped} 跳过、{t['failures']} 失败。")
lines += ['- 故障注入用例按生产配置跳过，不记作已执行；main 的功能验证来自同日冻结二进制的已完成验证，本轮重新执行的是性能测量。', '',
          '[构建与测试](versions.json) · [逐命令核验](command-audit.json) · [测试协议](protocol.json) · [客户端与执行器 SHA](harness-provenance.json)', '',
          '## 独立 perf 采样', '',
          '另对 100 MiB/key 的两种 List 增删和 ZRANK 各测两版，并补充 8 MiB RPUSH/LPOP 的两版采样，共 8 次；每次在既有 worker 上采集 25 秒、99 Hz task-clock/DWARF 栈。采样吞吐不进入上面的干净对照。CPU 占比包含轮询、内核及后台工作；含子调用的类别可重叠，也不能直接当作每请求 CPU 成本。', '',
          '| MiB/key / 操作 | 版本 | 样本 | 目录更新占比 | 目录构建占比 | 分配占比 | 复制占比 |',
          '|---|---|---:|---:|---:|---:|---:|']
for p in perf:
    cats = p['physical']['inclusive_categories_pct']
    lines.append(f"| {p.get('size',104857600)//1048576} / {p['operation']} | {p['version']} | {p['samples']:,} | {cats.get('directory_apply',0):.2f}% | {cats.get('directory_build',0):.2f}% | {cats.get('allocate',0):.2f}% | {cats.get('copy',0):.2f}% |")
lines += ['', '表中按未展开内联的实际函数帧归类，保留 OrderedGroupDirectory::Apply 等完整外层函数；展开内联后的详细视图也保存在 JSON，不能把缺少限定名的内联帧简单算成零目录开销。', '',
          '- 100 MiB LPUSH/RPOP：目录更新含子调用占比约 76.55% → 4.43%；RPUSH/LPOP 为 46.30% → 2.63%。main 的热点包含目录 Apply、整块 CowArray 构建和元数据 vector 追加。这支持“减少头尾变更后的目录重建”是大 List 收益的重要来源。',
          '- 8 MiB RPUSH/LPOP：目录更新占比也从 6.80% 降至 2.34%，并未显示目录重建成本增加。独立采样运行约 53,701 → 50,562 QPS（约 -5.8%），p99 22.27 → 35.56 ms；复现了回退方向，但未复现正式第三轮的全部跌幅。',
          '- 小 List 回退的根因尚未确定。当前 profile 含较多轮询与未解析符号，CPU 占比又不能表达 I/O 等待和逐请求成本；本轮没有隔离 ring、CowArray、坐标 overlay 和数据布局各自的影响。不能仅凭 PR 的分配方式变化就断言是哪一项造成回退。', '']
lines += ['', '[perf 汇总及热点符号](perf-summary.json) · [采样执行记录](profiles.json) · [采样文件校验值](perf-capture-index.json)', '',
          '从源码看，List ring 让容量足够时的头尾分裂/移除保留中间元数据；扩容和改变长度的中间拼接仍可能重建。排名查找通过成员索引取分数，再限定有序页区间并计算 Fenwick 前缀，避免旧路径从端点扫描无关页。以上测量比较的是整个 PR，不能分离 ring、COW chunk、常驻元数据缩减和物理坐标 overlay 分配各自的贡献。', '',
          '原始 perf 二进制及完整展开栈留在测试机，报告保留 SHA、命令、采样元数据、逐线程热点和汇总，不把巨大的采样文件加入仓库。', '',
          '## 复现与收尾', '',
          '[执行脚本](benchmark.py) · [负载执行器](run-random.py) · [客户端源码](random-client.cpp) · [原始 PR 补丁](pr289.patch) · [主机恢复核验](host-final.json) · [发布证据索引](evidence-index.json)', '',
          '脚本保留实际测试机器、冻结二进制、远端客户端和六块 scratch NVMe 白名单路径；移机需配置对应环境。测量后服务已停止，测试盘恢复内核驱动，hugepages 与 no-IOMMU 恢复。', '']
(W / 'README.md').write_text('\n'.join(lines))
print('PR289_REPORT_WRITTEN')
