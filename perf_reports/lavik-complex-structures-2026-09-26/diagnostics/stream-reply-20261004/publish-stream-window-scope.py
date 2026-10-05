"""Publish only a completed three-pair Stream-window scope with raw evidence."""
from pathlib import Path
import argparse,csv,hashlib,io,json,math,shutil,subprocess
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--scope',choices=['large-reads','large-writes','small-controls'],required=True)
p.add_argument('--resume-verified-snapshot',action='store_true',help='Reuse the retained scope only after matching its data and revalidating raw evidence')
a=p.parse_args();W=Path(__file__).parent;repo=Path('/mnt/dev/lavik-complex-refresh-20261004')
R=repo/'perf_reports/lavik-complex-structures-2026-09-26';D=R/'diagnostics/stream-reply-20261004'
source=W/'stream-window-followup-repeats.json';raw_source=source.read_bytes();v=json.loads(raw_source)
def selected(row):
 return (row['logical_bytes']==104857600 and (row['operation']!='XADD_MAXLEN' if a.scope=='large-reads' else row['operation']=='XADD_MAXLEN')) if a.scope!='small-controls' else row['logical_bytes']==65536
rows=[r for r in v['rows'] if selected(r)];expected=12 if a.scope=='large-writes' else 24
assert len(rows)==expected,(a.scope,len(rows),expected)
assert not any('error' in r for r in rows)
# Freeze exactly the scope before running the verifier: the live driver can
# append later scopes while this publication is being assembled.
tags={r['tag'] for r in rows};seed_tags=set()
for row in rows:
 raw=R/'raw'/('lavik-'+row['tag']);prefix=f'stream-{row["logical_bytes"]}-{row["field_bytes"]}'
 fill=json.loads((raw/(prefix+'.fill.json')).read_text())
 if row['operation']!='XADD_MAXLEN':seed_tags.add(fill['reused_seed_from'])
subset={**v,'rows':rows,'seeds':[s for s in v['seeds'] if s['tag'] in seed_tags],
        'scope':a.scope,'live_input_sha256_at_capture':hashlib.sha256(raw_source).hexdigest(),
        'scope_note':'Only this completed scope is published; other scopes may still be running. Original60point protocol is preserved in method.'}
assert {s['tag'] for s in subset['seeds']}==seed_tags
prefix='stream-window-'+a.scope
observations=W/(prefix+'-observations.json');summary_path=W/(prefix+'-summary.json')
if a.resume_verified_snapshot:
 retained=json.loads(observations.read_text())
 assert {k:v for k,v in retained.items() if k!='live_input_sha256_at_capture'}=={k:v for k,v in subset.items() if k!='live_input_sha256_at_capture'}
 subset=retained
else:
 assert not observations.exists() and not summary_path.exists(), 'inspect retained publication outputs before retrying'
 observations.write_text(json.dumps(subset,indent=2)+'\n')
subprocess.run(['python3',str(W/'summarize-stream-window.py'),'--input',str(observations),'--scope',a.scope,'--output',str(summary_path)],check=True)
summary=json.loads(summary_path.read_text());assert summary['observations']==expected
assert summary['input_sha256']==hashlib.sha256(observations.read_bytes()).hexdigest()
gap=json.loads((R/'diagnostics/main-a565d603-20261004/main-gap-summary.json').read_text())
peers=[]
for entry in summary['summary']:
 condition=f'stream-{entry["logical_bytes"]}-{entry["field_bytes"]}-k{entry["keys"]}'
 path=R/(condition+'-current.csv');digest=hashlib.sha256(path.read_bytes()).hexdigest()
 origin=next(row for row in gap['sources'] if row['condition']==condition)
 # Later candidates add Lavik series to the current CSV. Authenticate the
 # historical snapshot independently, then require every peer row unchanged.
 historical_commit='0a0431d2'
 historical=subprocess.check_output(['git','show',historical_commit+':'+str(path.relative_to(repo))],cwd=repo)
 assert hashlib.sha256(historical).hexdigest()==origin['csv_sha256']
 peer_names={'Redis','Valkey','Kvrocks (80 GiB cache)'}
 current_rows=list(csv.DictReader(io.StringIO(path.read_text())))
 historical_rows=list(csv.DictReader(io.StringIO(historical.decode())))
 assert [r for r in current_rows if r['series'] in peer_names]==[r for r in historical_rows if r['series'] in peer_names]
 matches=[r for r in current_rows if r['command']==entry['operation'] and int(r['connections'])==entry['connections'] and r['series'] in peer_names]
 assert len(matches)==3 and len({r['series'] for r in matches})==3 and all(not r['error'] for r in matches)
 values={r['series']:{k:float(r[k]) for k in ['qps','p99_ms']} for r in matches}
 assert all(math.isfinite(x['qps']) and x['qps']>0 for x in values.values())
 fastest=max(values,key=lambda k:values[k]['qps'])
 peers.append({'condition':condition,'command':entry['operation'],'connections':entry['connections'],
               'csv':path.name,'csv_sha256':digest,'historical_csv_commit':historical_commit,'historical_csv_sha256':origin['csv_sha256'],'all_peer_rows_unchanged':True,'historical_peers':values,
               'window_median_qps':entry['window_median_qps'],'fastest_historical_peer':fastest,
               'window_to_fastest_historical_peer':entry['window_median_qps']/values[fastest]['qps']})
paths=[]
for name,content in [(prefix+'-observations.json',subset),(prefix+'-summary.json',summary),(prefix+'-historical-context.json',peers)]:
 path=D/name;assert not path.exists();path.write_text(json.dumps(content,indent=2)+'\n');paths.append(path)
for name in ['summarize-stream-window.py','publish-stream-window-scope.py']:
 shutil.copyfile(W/name,D/name);paths.append(D/name)
for tag in sorted(tags|seed_tags):
 raw=R/'raw'/('lavik-'+tag)
 paths.extend(sorted(raw.glob('*.json')))
 paths.extend(sorted(raw.glob('*.info-*.txt')))
label={'large-reads':'100 MiB / 128 B / 8 keys 读取','large-writes':'100 MiB / 128 B / 8 keys 写入','small-controls':'64 KiB / 1024 B / 64 keys 读写控制'}[a.scope]
lines=[f'# Stream 页面窗口：{label}','',
       f'[{expected} 个原始观测]({prefix}-observations.json) · [完整配对摘要]({prefix}-summary.json) · [历史对照与 CSV 哈希]({prefix}-historical-context.json)','',
       '固定父版本 `adec3a34` 与候选 `5b9ebded`，生产 native/SPDK、测试与故障注入关闭。三轮 A/B、B/A、A/B，每点 30 秒、pipeline=1、12 workers。读取共用每轮父版本新建的逻辑数据，各版本分别重启且不夹写入；后台物理变化仍可能存在。写入各版本独立新建数据，后续并发档继承前档的写入。每个观测已逐字段核对原始 result、二进制 SHA、全部 key 基数、错误与正常退出；读种子来源及前后基数另行核对。压测不与编译、测试或 perf 重叠。','',
       '表中百分比是逐轮配对变化的中位数和范围，不是置信区间，也不一定等于两列边际 QPS 中位数的比值。负 p99 变化表示改善。全量读取每点完成命令较少、QPS 舍入到两位，尤其不能把 p99 当作高精度尾分位估计。','',
       '| 命令 | 并发 | 父 QPS | 窗口 QPS | 配对 QPS 变化：中位数（范围） | 父/窗口 p99 ms | 配对 p99 变化：中位数（范围） |',
       '|---|---:|---:|---:|---:|---:|---:|']
for entry in summary['summary']:
 q,t=entry['qps_paired_percent'],entry['p99_paired_percent']
 lines.append(f'| {entry["operation"]} | {entry["connections"]} | {entry["parent_median_qps"]:,.2f} | {entry["window_median_qps"]:,.2f} | {q["median"]:+.2f}% ({q["min"]:+.2f}% … {q["max"]:+.2f}%) | {entry["parent_median_p99_ms"]:.3f} / {entry["window_median_p99_ms"]:.3f} | {t["median"]:+.2f}% ({t["min"]:+.2f}% … {t["max"]:+.2f}%) |')
lines+=['','## 与三库历史同负载的距离','',
        '只匹配命令、每 key 字节数、元素大小、key 数和并发，其他三库没有在本轮重跑。Redis/Valkey 关闭持久化，Kvrocks 关闭 WAL、配置 80 GiB cache，Lavik 保持 SPDK 持久化且无 payload cache；历史单次扫描和本轮三次 30 秒配对方法不同。单个比值达到或超过 100% 不能代表同等持久性排名或全部复杂命令已经达标。','',
        '| 命令 | 并发 | 窗口 QPS 中位数 | Redis | Valkey | Kvrocks | 窗口/最快历史对照 |','|---|---:|---:|---:|---:|---:|---:|']
for entry in peers:
 values=entry['historical_peers']
 lines.append(f'| {entry["command"]} | {entry["connections"]} | {entry["window_median_qps"]:,.2f} | {values["Redis"]["qps"]:,.2f} | {values["Valkey"]["qps"]:,.2f} | {values["Kvrocks (80 GiB cache)"]["qps"]:,.2f} | {entry["window_to_fastest_historical_peer"]:.2%} |')
lines+=['','这里只汇总标题所示的完整范围，其余范围状态见[总报告](README.md)。PR #275 保持草稿；原生产 RDB 超时仍未解释，完整正确性和失败证据保留在总报告。#270 与 #275 的独立增益不能相乘或转记为组合版本收益。','']
path=D/(prefix+'.md');assert not path.exists();path.write_text('\n'.join(lines));paths.append(path)
# Keep scope-specific conclusions visible without claiming unfinished controls.
p=D/'README.md';s=p.read_text();anchor='## 后续方案与当前测量\n';assert anchor in s
section=f'## #275 {label}三轮对照完成\n\n[{expected} 点完整配对、QPS/p99 与历史三库比较]({prefix}.md)。所有轮次和不利结果均保留；这只证明该范围完成，不代表剩余控制已通过或整体性能目标已达到。\n\n'
assert section not in s;p.write_text(s.replace(anchor,section+anchor));paths.append(p)
paths=list(dict.fromkeys(paths));assert all(p.stat().st_size<3*1024**2 for p in paths)
relative=[str(p.relative_to(repo)) for p in paths]
subprocess.run(['git','diff','--check','--',*relative],cwd=repo,check=True)
subprocess.run(['git','add','-f','--',*relative],cwd=repo,check=True)
(W/(prefix+'-publication-files.json')).write_text(json.dumps(relative,indent=2)+'\n')
print('STAGED',a.scope,len(paths),'files',sum(p.stat().st_size for p in paths),'bytes')
