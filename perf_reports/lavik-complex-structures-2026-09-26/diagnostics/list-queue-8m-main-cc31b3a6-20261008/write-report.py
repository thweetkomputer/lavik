from pathlib import Path
import csv,json
W=Path(__file__).parent
experiments=[('combined','同时省略 RPUSH / 未删空页 pop 的邻页','/mnt/dev/lavik-rpush-lpop-20261008','queueopt'),('push-only','只省略 RPUSH 的前邻页','/mnt/dev/lavik-rpush-only-20261008','pushopt'),('pop-only','只省略未删空页 pop 的邻页','/mnt/dev/lavik-lpop-only-20261008','popopt')]
decision=json.loads((W/'decision.json').read_text())
lines=['# 8 MiB/key RPUSH/LPOP：合并后 main 的邻页读取优化实验','',decision['conclusion'],'','## 版本与测试范围','','- 基线：合并 #289 后的 main `cc31b3a6250d0fcf2fa0d985b1ece3a8602e09f9`。其 Git tree 与已验证的 #289 `c8f128dc` 完全相同，因此复用同一 SHA256 的冻结生产二进制；源树等价关系记录在每组 `versions.json`。所有 main 观测均为本次重新测量。','- 每个 key 初始 8 MiB：8192 个 1 KiB 元素，共 8 个 key。320 连接、16 个客户端线程、pipeline=1、30 秒。每次独立随机选 key，并以 50/50 概率选择 RPUSH 或 LPOP；不强制配对。QPS 按命令数计算。','- 每个观测都新启服务、清空并重新准备允许使用的六块 SPDK 设备、重新填充数据并等待事务清理。服务端 12 workers，16 vCPU 配额，无 payload cache。每一对使用相同的进程 digest seed 和客户端种子，三轮交替 main/候选、候选/main、main/候选。','- 三种候选各有三组新测对照，共 18 个常规性能观测；另有 3 次最初 main 复现、6 次独立 perf 采样。perf 不计入 QPS/p99 对照。未测 5120 连接。','- 每条响应、客户端/服务端命令数、push/pop 比例、最终逐 key 元素数（初值 + push − pop）、[0.5N, 2N] 边界以及正常退出均检查通过。生产 CMake cache、Bycorf 依赖和编译参数一致。','','## 三种候选的结果','','增幅取三个 **候选/main 配对比值的中位数**；它不必等于两列独立中位数之比。','','|候选|main QPS 中位数|候选 QPS 中位数|配对 QPS 变化|main p99 中位数|候选 p99 中位数|配对 p99 变化|结论|','|---|---:|---:|---:|---:|---:|---:|---|']
summary_rows=[]
for name,title,path,label in experiments:
 p=Path(path);s=json.loads((p/'summary.json').read_text());assert json.loads((p/'audit.json').read_text())['passed']
 m,c=s['versions']['main'],s['versions'][label]
 row={'variant':name,'main_qps_median':m['qps'],'candidate_qps_median':c['qps'],'paired_qps_change_pct':100*(s['qps_ratio_median']-1),'main_p99_ms_median':m['p99_ms'],'candidate_p99_ms_median':c['p99_ms'],'paired_p99_change_pct':100*(s['p99_ratio_median']-1),'decision':decision[name]};summary_rows.append(row)
 lines.append(f'|{title}|{m["qps"]:,.0f}|{c["qps"]:,.0f}|{row["paired_qps_change_pct"]:+.1f}%|{m["p99_ms"]:.2f} ms|{c["p99_ms"]:.2f} ms|{row["paired_p99_change_pct"]:+.1f}%|{decision[name]}|')
lines+=['','## 实现与正确性','','原路径预先加载目标页的相邻页，以便分裂或退休页面时修改完整页面的链接。三个候选分别省略确定不会变化的邻页：尾部插入保留原尾页 ID；单页 pop 若留下非空页面，则两侧链接均不变。若删除整页或确实改动链接，规划器仍要求对应邻页快照。所有已提供页面仍检查版本、身份、链接和内容；Sorted Set 的跨页有序性校验保持完整。','','目录规划器、公共 API 注释和对应架构陈述一起修改；既有穷举测试扩展为在相同 180 种 splice 组合中比较“完整加载”和“只加载必要页面”的完整写入后像，再验证事务提交与恢复结果。三个实验的独立补丁见 [combined.patch](combined.patch)、[push-only.patch](push-only.patch)、[pop-only.patch](pop-only.patch)。','','- 第一版：244 项单元测试、75 项有序集合/恢复集成测试和 16 项 Hash 集成测试通过。故障注入关闭，分别跳过 36 / 20 项依赖注入的集成测试。','- 后两版仅调整运行时页面选择，规划器及单元测试源文件与第一版相同；各重新运行 12 项 List/有序写集成测试，4 项故障注入用例按配置跳过。','- 修改的 C++ 文件通过 clang-format 23.1.1 检查。','','## 逐轮证据与 perf','','三次最初 main 复现为 39,350 / 58,034 / 57,321 QPS，p99 为 73.62 / 21.19 / 20.95 ms。慢轮提交队列峰值为 3147；另两轮为 210 / 294。后续各组 main 也有明显波动。因此未把一次低基线当作收益，未把队列峰值与尾延迟的相关性当作根因证明。','','perf 使用每 worker 99 Hz task-clock、25 秒、DWARF 调用栈；下表为保留完整函数名的物理调用栈中页面加载/解码的 inclusive CPU 占比。占比包含轮询、内核及后台工作，并非 CPU/命令或 I/O 等待时间；各版本处理的请求数不同，不能直接据此推导延迟改善。']
for name,title,path,label in experiments:
 p=Path(path);rows=json.loads((p/'pairs.json').read_text());profiles=json.loads((p/'profiles.json').read_text());perf=json.loads((p/'perf-summary.json').read_text())
 lines+=['',f'### {title}','','|轮次|版本|QPS|p99 ms|提交队列峰值（测量前 → 后）|原始数据|','|---:|---|---:|---:|---:|---|']
 for r in rows:
  d=Path(r['raw']);v=r['result'];stem=next(d.glob('*.result.json')).name
  def info(n):return dict(x.split(':',1) for x in next(d.glob('*.info-'+n+'.txt')).read_text().splitlines() if ':' in x)
  b,a=info('before'),info('after')
  lines.append(f'|{r["round"]-3}|{r["version"]}|{v["qps"]:,.0f}|{v["p99_ms"]:.3f}|{b["tx_commit_queue_peak"]} → {a["tx_commit_queue_peak"]}|[结果](../../raw/{d.name}/{stem})|')
 lines+=['','|perf 版本|诊断 QPS|诊断 p99 ms|页面加载 CPU 占比|解码 CPU 占比|','|---|---:|---:|---:|---:|']
 for r in profiles:
  stats=next(x for x in perf if x['version']==r['version'])['physical']['inclusive_categories_pct'];v=r['result']
  lines.append(f'|{r["version"]}|{v["qps"]:,.0f}|{v["p99_ms"]:.3f}|{stats.get("ordered_page_read",0):.2f}%|{stats.get("decode",0):.2f}%|')
 lines += ['',f'[审计]({name}/audit.json) · [逐轮摘要]({name}/summary.json) · [perf 摘要]({name}/perf-summary.json) · [版本和构建]({name}/versions.json) · [测量脚本]({name}/pairs.py)']
lines+=['','## 范围与复现','','这是 c320、8 MiB/key 的 RPUSH/LPOP 专项实验，不代表其他并发或大小的收益；没有用这些结果替换四系统全量 main 曲线。最新合并状态已补充到原 #289 报告。命令、冻结二进制 SHA、相同种子验证、原始 INFO、客户端结果、编译及测试日志随报告保存；原始大体积 perf.data 留在测试主机，仓库保留采样命令和符号摘要。测试后六块 NVMe 均恢复内核驱动，hugepages 归零，未遗留服务进程。','']
(W/'README.md').write_text('\n'.join(lines))
with (W/'summary.csv').open('w') as f:
 writer=csv.DictWriter(f,fieldnames=list(summary_rows[0]));writer.writeheader();writer.writerows(summary_rows)
(W/'summary.json').write_text(json.dumps(summary_rows,indent=2)+'\n')
