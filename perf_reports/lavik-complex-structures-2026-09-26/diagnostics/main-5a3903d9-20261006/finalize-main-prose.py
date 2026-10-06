"""Write the reviewed full-refresh narrative only after all measurements finish."""
from pathlib import Path
import csv
import importlib.util
import json
import shutil

W = Path(__file__).parent
R = Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26')
D = R / 'diagnostics/main-5a3903d9-20261006'
assert 'ALL_MAIN_GRIDS_AND_IMPORTS_COMPLETE' in (W / 'main-refresh-driver.log').read_text()
m = json.loads((R / 'current-main.json').read_text())
g = json.loads((D / 'main-gap-summary.json').read_text())
assert m['target_main'] == g['main_commit'] == '5a3903d9b3c0632e3b34e827b779d9daa58455c2'
assert g['conditions'] == 28 and g['points'] == 332
failed = [p for p in g['points_detail'] if p['main_error']]
imports = json.loads((R / 'current-imports.json').read_text())
assert len(imports['plots']) == 4 and all(p['main']['fresh'] for p in imports['plots'])

lines = [
    '# main `5a3903d9` 完整复测', '',
    f'2026-10-06 固定 main `'+m['target_main']+f'`，完成原报告全部 28 组吞吐条件：332 个测点，{332-len(failed)} 个成功、{len(failed)} 个失败；另完成 4/4 组批量导入。这里没有混入未合并 PR，也没有从不同提交挑选最快结果。', '',
    '[主报告](../../README.zh-CN.md) · [逐命令差距与逐点限制](main-gap-summary.md) · [构建与硬件](host-and-build.json) · [绘图数据核验](report-audit.json) · [实际命令计数核验](main-command-audit.json) · [完整文件哈希](main-evidence-index.json)', '',
    '## 测量范围', '',
    'List、Stream、ZSet 覆盖 64 KiB、1 MiB、100 MiB/key，各有 128 B 与 1024 B 元素；Hash/Set 覆盖 1 MiB/50,000 keys 与 100 MiB/500 keys，各有两种元素大小；另有两组扩展键数的 LSET。点操作使用 c80/320/1280/2560/5120，全量读取使用小对象 c16/80 或大对象 c1/4/16。每点配置 8 秒，扩展 LSET 为 10 秒，pipeline=1。运行顺序、预置及客户端命令均保留于原始记录。', '',
    'Lavik 使用 AMD EPYC 9V74、16 vCPU、12 workers、六块 NVMe SPDK 持久化、8 GiB EAL，关闭测试故障注入。编译器、生产二进制及 SHA-256 与 [PR #283 对照的 main](../pr283-main-20261006/matched-build-proof.json) 相同。Hash/Set 命令扫描使用 RESTORE 预置后重启；RESTORE 耗时不作为批量 HSET/SADD 导入成绩。每个条件独立预置，校验全部 key 基数并核对服务退出。', '',
    'Redis、Valkey、Kvrocks 本轮未重跑，图表保留历史测量日期、原始数据和身份。Redis/Valkey 关闭持久化，Kvrocks 关闭 WAL 且有 80 GiB cache；这些条件与 Lavik 的持久化设置不同。单次扫描没有置信区间，不能据此宣称在等同持久性下追平另外三个系统。', '',
    '## 批量导入', '',
    '每组 50,000 keys、1 MiB/key，8 个客户端、pipeline=64、每命令约 16 KiB 元素。总耗时包含逐命令 RESP 编码和客户端处理；不是服务器独立吞吐上限。表中单位为秒，越低越好。', '',
    '| 类型 / 元素大小 | main | Redis（历史） | Valkey（历史） | Kvrocks（历史） |',
    '|---|---:|---:|---:|---:|',
]
for c in imports['plots']:
    name = f'{c["kind"]}-{c["size"]}-{c["field"]}-k{c["keys"]}-fill.csv'
    values = {row['product']: float(row['seconds']) for row in csv.DictReader((R / name).open())}
    assert set(values) == {'lavik', 'redis', 'valkey', 'kvrocks'}
    lines.append(f'| {c["kind"]} / {c["field"]} B | ' + ' | '.join(f'{values[p]:,.2f}' for p in ('lavik','redis','valkey','kvrocks')) + ' |')
lines += ['', '## 失败与历史问题', '']
if failed:
    lines += ['以下失败保留在图表、CSV 和原始证据中，不以零 QPS 代替，也不从总测点数中删除。', '']
    lines += [f'- `{p["condition"]}` / {p["command"]} / c{p["connections"]}：见原始错误与逐点汇总。' for p in failed]
else:
    lines += ['本轮 332 个吞吐测点均完成，全部 main 服务干净退出。', '']
lrange = next(p for p in g['points_detail'] if p['condition'] == 'list-104857600-128-k8' and p['command'] == 'LRANGE' and p['connections'] == 16)
if not lrange['main_error']:
    lines += [f'旧报告失败的 100 MiB List、128 B 元素、c16 全量 LRANGE，本轮为 {lrange["main_qps"]:.2f} QPS、p99 {lrange["main_p99_ms"]:.3f} ms。这是本次观测，不单独证明历史内存准入问题已彻底解决。[历史诊断](../main-refresh-20261004/list-lrange-admission.md) 保留原始失败。', '']
lines += [
    '原生验证曾因系统 `/tmp` 空间不足导致 RDB scratch ENOSPC。随后在私有 mount namespace 内使用数据盘临时目录；main、候选和本轮扫描均使用同一策略，宿主机 `/tmp` 不变。原始失败与修复后的结果分别保留于 [原生验证说明](../pr283-main-20261006/README.md)，没有修改生产代码、延长超时或排除失败用例。', '',
    '## 与 PR #283 的关系', '',
    '[#283 的 144 点三轮配对与四组独立 perf](../pr283-main-20261006/README.md) 使用同一 main。小对象 ZINCRBY c320/c5120 的配对 QPS 中位数分别 +1.80% / +1.57%，三轮均升；大对象四档 ZINCRBY 和全部 ZADD 条件的 QPS 方向混合。小对象 ZSCORE c320 的配对中位数为 −36.12%，p99 中位 +315.15%，原因未确定。候选有局部收益，但尚无稳定整体写入收益，保持 draft。', '',
    '这组 30 秒三轮配对与本页 8/10 秒单次扫描分开解释；四组 perf 仅覆盖 ZINCRBY c80，不解释读取异常，不混入吞吐图。', '',
    '## 复现与证据', '',
    '[完整执行顺序](refresh-main.py) · [吞吐运行器](run-condition.py) · [导入运行器](run-import.py) · [实际命令日志](commands.jsonl) · [完成日志](main-refresh-driver.log) · [绘图和来源选择](render-main-refresh.py) · [数据核验脚本](audit-current.py)。运行脚本保留此次工作区、二进制、数据盘 allowlist 和共享主机锁路径；移机时需先准备相应环境。每个条件的主机配置与恢复快照也保存在本目录。', '',
    '此前 main 与导入清单保存在 `previous-current-main.json`、`previous-current-imports.json`，旧绘图入口的清单也各有快照。原始 CLI、INFO 空行和日志保持字节不变；文件索引记录长度与 SHA-256。', '',
]
(D / 'README.md').write_text('\n'.join(lines))
link = 'diagnostics/pr283-main-20261006/README.md'
m['notes'] = {
    'zh': f'[#283 对 rebase 后 main 的三轮配对]({link})已完成：小对象 ZINCRBY c320/c5120 分别 +1.80% / +1.57%，但整体写入收益不稳定；小对象 ZSCORE c320 出现未解释下降（配对中位 −36.12%，p99 +315.15%）。目前保持 draft，详细结果包含不利观测和独立 perf。',
    'en': f'[Three paired rounds of #283 versus its rebased main]({link}) are complete: small ZINCRBY c320/c5120 gain +1.80% / +1.57%, but overall write gains are inconsistent. Small ZSCORE c320 has an unresolved slowdown (paired median −36.12%, p99 +315.15%). The PR remains draft; full results retain unfavorable observations and separate perf evidence.',
}
(R / 'current-main.json').write_text(json.dumps(m, indent=2) + '\n')
spec = importlib.util.spec_from_file_location('plot', R / 'plot_current_main.py')
plot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plot)
for zh, name in [(True, 'README.zh-CN.md'), (False, 'README.md')]:
    (R / name).write_text(plot.readme(m, zh))
pr = R / 'diagnostics/pr283-main-20261006/README.md'
text = pr.read_text().replace('main 全量刷新仍在运行。', 'main 全量刷新已完成：28/28 组吞吐、4/4 组导入，见 [本轮 main 测量](../main-5a3903d9-20261006/README.md)。')
pr.write_text(text)
shutil.copyfile(__file__, D / Path(__file__).name)
print('Wrote full main narrative and bilingual report introductions.')
