"""Build a current-main narrative only from completed and validated observations."""
from pathlib import Path
import csv,hashlib,importlib.util,json,shutil,statistics
W=Path(__file__).parent
R=Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26')
D=R/'diagnostics/main-920f879b-20261006'
assert 'ALL_MAIN_GRIDS_AND_IMPORTS_COMPLETE' in (W/'main-refresh-driver.log').read_text()
m=json.loads((R/'current-main.json').read_text());g=json.loads((D/'main-gap-summary.json').read_text());v=json.loads((W/'versions.json').read_text())['main']
assert m['target_main']==g['main_commit']==v['commit']=='920f879b05636d066ef0485f1ee1121813ef79ac'
assert g['conditions']==28 and g['points']==332
# Compare each exact grid point with its prior report observation, retaining failures.
old=json.loads((R/'diagnostics/main-5a3903d9-20261006/main-gap-summary.json').read_text())
old_points={(p['condition'],p['command'],p['connections']):p for p in old['points_detail']}
changes=[]
for p in g['points_detail']:
 q=old_points[(p['condition'],p['command'],p['connections'])]
 change={k:p[k] for k in ['condition','command','connections']}
 change.update(previous_qps=q['main_qps'],current_qps=p['main_qps'],previous_p99_ms=q['main_p99_ms'],current_p99_ms=p['main_p99_ms'],previous_error=q['main_error'],current_error=p['main_error'])
 change['qps_change_percent']=None if p['main_error'] or q['main_error'] else (p['main_qps']/q['main_qps']-1)*100
 change['p99_change_percent']=None if p['main_error'] or q['main_error'] else (p['main_p99_ms']/q['main_p99_ms']-1)*100
 changes.append(change)
comparison={'previous_main':old['main_commit'],'current_main':m['target_main'],'method':'Two independent single scans, not paired repeated measurements. Same grid; process digest seeds and physical layouts can vary, particularly Hash/Set. Changes cannot establish individual PR effects or statistical significance. Failed observations stay explicit.','points':changes}
(D/'previous-main-comparison.json').write_text(json.dumps(comparison,indent=2)+'\n')
lines=['# 与上一轮 main 的观测对比','','比较 `5a3903d9` 与 `920f879b` 的相同负载。两轮都是单次扫描，不是同期交替配对；Hash/Set 种子与物理布局可能不同，不能把变化归因于某个 PR。失败点保留，比例仅对两边都成功的点计算。','','| 命令 | 可比较点数 | 逐点 QPS 变化中位 | QPS 变化范围 | 逐点 p99 变化中位 |','|---|---:|---:|---:|---:|']
for op in sorted({p['command'] for p in changes}):
 values=[p['qps_change_percent'] for p in changes if p['command']==op and p['qps_change_percent'] is not None]
 tails=[p['p99_change_percent'] for p in changes if p['command']==op and p['p99_change_percent'] is not None]
 if values:lines.append(f'| {op} | {len(values)} | {statistics.median(values):+.2f}% | {min(values):+.2f}% ～ {max(values):+.2f}% | {statistics.median(tails):+.2f}% |')
lines+=['','[全部逐点 QPS、p99 和错误](previous-main-comparison.json)。这里的中位数不是总 QPS 的变化，也不是所有负载均有同等收益；p99 负值表示改善。','']
(D/'previous-main-comparison.md').write_text('\n'.join(lines))
failed=[p for p in g['points_detail'] if p['main_error']]
lines=['# 合并后 main `920f879b` 完整复测','',f'固定提交 `{m["target_main"]}`，28/28 组吞吐条件共 332 个测点，{332-len(failed)} 成功、{len(failed)} 失败；另完成 4/4 组批量 HSET/SADD 导入。包含已合并的 #275、#282、#285，以及 main 上的其他变更。#283 已关闭未合并，不纳入本轮。','',
'[主报告](../../README.zh-CN.md) · [与上轮 main 的观测对比](previous-main-comparison.md) · [与另外三库的逐命令差距](main-gap-summary.md) · [构建与硬件](host-and-build.json) · [功能测试](versions.json) · [绘图核验](report-audit.json) · [命令计数核验](main-command-audit.json) · [证据索引](main-evidence-index.json)','','## 测量范围与解释','',
'List、Stream、ZSet 覆盖 64 KiB、1 MiB、100 MiB/key，各有 128 B 与 1024 B 元素；Hash/Set 覆盖 1 MiB/50,000 keys 与 100 MiB/500 keys，各有两种元素大小；另有两组扩展键数的 LSET。点操作使用 c80/320/1280/2560/5120，全量读取使用小对象 c16/80、大对象 c1/4/16。每点 8 秒，扩展 LSET 为 10 秒，pipeline=1。','',
'同一台 AMD EPYC 9V74、16 vCPU 主机，12 个服务 worker、六块授权 NVMe、SPDK 持久化、8 GiB EAL。生产二进制关闭测试故障注入，记录 GCC/native/LTO 配置、主源码和 Bycorf/子模块身份。编译和功能验证在压测前完成，没有与压测并行。临时目录通过独立挂载命名空间使用工作盘，宿主 `/tmp` 不变。','',
'各条件独立预置并逐 key 核验。Hash/Set 命令扫描使用 RESTORE 后重启，其预置时间不计作批量 HSET/SADD 成绩。本轮沿用原图表协议，没有采用固定 digest seed 的专门对照；因此与旧 main 的差异也可能包含路由布局和后台工作变化，不能直接解释为某个合并 PR 的收益。','',
'其他三个系统本轮未重跑。Redis/Valkey 关闭持久化；Kvrocks 关闭 WAL，使用无压缩 RAID0 和 80 GiB cache；Lavik 不缓存字段或页内容。图表保留历史源数据，不能据此宣称同等持久性下追平。此次没有新增 perf 采样；旧 PR 的 perf 和三轮对照保留原始提交身份，不能转记为当前 main 的热点或吞吐。','',
'合并前 #275 的小 Stream 全量读取尾延迟回退，以及 #285 的分散 Hash 写入/写后读取代价，均保留在历史报告中。合并状态不等于这些代价已消除，本轮当前 main 的实际结果全部呈现。','',
'## 功能验证','']
def counts(value):
 skips=sum(t.get('result')=='SKIPPED' for suite in value.get('testsuites',[]) for t in suite.get('testsuite',[]))
 return value['tests']-value['failures']-skips,skips,value['failures']
for name,t in v['tests'].items():
 passed,skipped,failures=counts(t);lines.append(f'- `{name}`：{passed} 通过、{skipped} 跳过、{failures} 失败。')
lines+=['','上述是本机生产构建验证；故障注入用例的跳过不算成功执行。CI 状态见 [当前固定提交的 CI](https://github.com/eloqdata/lavik/actions/runs/37486998302) 与本目录的状态快照，不以吞吐通过替代功能覆盖。','', '## 批量导入','',
'每组 50,000 keys、1 MiB/key，8 个客户端、pipeline=64、每命令约 16 KiB 元素；时间包含逐命令 RESP 编码和客户端处理。单位为秒，越低越好。','','| 类型 / 元素大小 | main | Redis（历史） | Valkey（历史） | Kvrocks（历史） |','|---|---:|---:|---:|---:|']
imports=json.loads((R/'current-imports.json').read_text())
for c in imports['plots']:
 values={row['product']:float(row['seconds']) for row in csv.DictReader((R/f'{c["kind"]}-{c["size"]}-{c["field"]}-k{c["keys"]}-fill.csv').open())}
 lines.append(f'| {c["kind"]} / {c["field"]} B | '+' | '.join(f'{values[p]:,.2f}' for p in ['lavik','redis','valkey','kvrocks'])+' |')
lines+=['','## 失败、收尾与复现','']
if failed:
 lines+=['以下失败留在 CSV、图表和原始日志中；不记为零 QPS，也不删除后挑选重跑值。','']+[f'- `{p["condition"]}` / {p["command"]} / c{p["connections"]}。' for p in failed]
else:lines+=['本轮 332 个吞吐测点均成功完成；所有服务正常退出。']
lines+=['','六块 scratch NVMe 已恢复原驱动与主机设置，见 [收尾核验](host-final.json)。主机运行状态文件不随报告提交。','',
'[执行顺序](refresh-main.py) · [吞吐运行器](run-condition.py) · [导入运行器](run-import.py) · [构建与功能测试](validate-native.py) · [命令日志](commands.jsonl) · [完成日志](main-refresh-driver.log) · [绘图](render-main-refresh.py) · [核验](audit-current.py)。脚本保留本次工作区、二进制、数据盘白名单和主机锁路径；移机时需准备对应环境。','',
'绘图使用已有的独立 Python 环境，版本见 [绘图环境](render-environment.json)。首次后处理因系统 Python 缺少 matplotlib 而停止；切换绘图环境后完成，未重跑或修改测量数据。原始异常日志保留。','',
'旧版清单保存在 `previous-current-main.json`、`previous-current-imports.json` 及其他 `previous-*.json` 中。原始数据不改名、不覆盖；旧 PR 报告作为历史记录保留。','']
ci=json.loads((W/'current-ci.json').read_text())
assert ci['headSha']==m['target_main']
lines += ['', 'CI 快照：`'+ci['status']+'` / `'+(ci['conclusion'] or 'pending')+'`，'+str(sum(j['conclusion']=='success' for j in ci['jobs']))+' 项任务成功；完整任务列表见 [current-ci.json](current-ci.json)。后续状态以固定运行链接为准。', '']
(D/'README.md').write_text('\n'.join(lines))
# Link all historical evidence from the new manifest without retaining old draft claims.
m['notes']={'zh':'[与上一轮 main 的 QPS/p99 对比](diagnostics/main-920f879b-20261006/previous-main-comparison.md)。#275、#282、#285 已合并；#283 已关闭未合并。当前图表均重测自上述 main。历史证据：[Stream 三轮对照](diagnostics/pr275-main-20261006/README.md)、[Hash/Set 三轮与 perf](diagnostics/hashset-routing-overlay-20261006/README.md)、[长 key 优化](diagnostics/list-reply-reserve-20261004/README.md)。历史草稿建议和数值仅适用于当时提交。','en':'[QPS/p99 comparison with the preceding main](diagnostics/main-920f879b-20261006/previous-main-comparison.md). #275, #282 and #285 are merged; #283 is closed without merging. All current charts are freshly measured on this main. Historical evidence: [Stream paired comparison](diagnostics/pr275-main-20261006/README.md), [Hash/Set paired results and perf](diagnostics/hashset-routing-overlay-20261006/README.md), [long-key optimization](diagnostics/list-reply-reserve-20261004/README.md). Historical draft recommendations and measurements apply to their named revisions.'}
(R/'current-main.json').write_text(json.dumps(m,indent=2)+'\n')
spec=importlib.util.spec_from_file_location('plot',R/'plot_current_main.py');plot=importlib.util.module_from_spec(spec);spec.loader.exec_module(plot)
for zh,name in [(True,'README.zh-CN.md'),(False,'README.md')]:
 text=plot.readme(m,zh)
 text=text.replace('rebase 后 #283 与 main：配对结果、perf 及验证','已关闭 #283 的历史配对、perf 及验证').replace('Rebased PR #283 versus main: paired results, perf and validation','Closed PR #283: historical paired results, perf and validation').replace('PR 去留与原始失败记录','历史 PR 去留与原始失败记录').replace('PR disposition and retained failure records','Historical PR disposition and retained failure records')
 (R/name).write_text(text)
# Include finalized scripts and native/CI proof, excluding temp data and binaries.
for p in W.iterdir():
 if p.is_file() and p.suffix in ['.py','.json','.log','.txt'] and p.name not in ['main-publish-paths.json','session-checkpoint.json']:
  shutil.copyfile(p,D/p.name)
print('Finalized new main narrative and comparison; audit and publication still required.')
