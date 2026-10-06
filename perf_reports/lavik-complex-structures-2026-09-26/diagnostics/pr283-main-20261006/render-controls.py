"""Render every paired result, with original absolute values and adverse rounds."""
import argparse
import hashlib
import json
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--observations', type=Path, required=True)
p.add_argument('--validation', type=Path, required=True)
p.add_argument('--audit', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
obs = json.loads(a.observations.read_text())
v = json.loads(a.validation.read_text())
audit = json.loads(a.audit.read_text())
digest = hashlib.sha256(a.observations.read_bytes()).hexdigest()
assert v['input_sha256'] == audit['input_sha256'] == digest
assert len(obs['rows']) == v['observations'] == audit['observations'] == 144
assert len(v['summary']) == 24 and v['status'] == 'complete three-pair scope verified'
lines = ['# PR #283：rebase 后与 main 的完整配对对照', '',
         'main `5a3903d9` 对比其直接子提交 `ace4198b`。24 个条件各三轮 A/B、B/A、A/B；配置 `--test-time=30`、pipeline=1、12 workers。高延迟时在途请求排空可延长实际运行，逐轮表保留客户端调用总耗时，精确 memtier duration 见命令核验 JSON。QPS 使用 memtier 报告值，不用请求数除以固定 30 秒。', '',
         '读对共享新建父版本逻辑数据并分别重启，写对分别新建；不是不可变物理快照。ZADD CH 为八个成员的 0/1 分值切换，并发时可包含同分值 no-op，因此这里只报告命令吞吐。', '',
         '绝对值为各版本三轮中位数，百分比为三轮配对变化的中位数，不能互换。QPS 越高越好，p99 越低越好；三轮不构成统计置信区间。其他系统未重跑；本表不能用于宣称整体追平。', '',
         '| 数据字节 / 成员字节 / keys / 初始分值 | 命令 / 并发 | main QPS | #283 QPS | 配对变化 | main p99 ms | #283 p99 ms | 配对变化 |',
         '|---|---|---:|---:|---:|---:|---:|---:|']
for row in v['summary']:
    label = ' / '.join(str(row[k]) for k in ('logical_bytes', 'field_bytes', 'keys', 'layout'))
    lines.append(f'| {label} | {row["operation"]} / {row["connections"]} | {row["parent_median_qps"]:.2f} | {row["candidate_median_qps"]:.2f} | {row["qps_paired_percent"]["median"]:+.2f}% | {row["parent_median_p99_ms"]:.3f} | {row["candidate_median_p99_ms"]:.3f} | {row["p99_paired_percent"]["median"]:+.2f}% |')
lines += ['', '## 调用总耗时的辅助吞吐口径', '',
          '下面以完成请求数除以外层客户端调用秒数，包含远端启动、SSH 和请求排空，不能视为服务器单独吞吐。memtier 的 Runtime 与外层调用耗时分别保留，不假定二者相同；高排队测点尤其需要结合此表和 p99 审查。这里不更改上表的 memtier QPS 定义。', '',
          '| 数据字节 / 成员字节 / keys / 初始分值 | 命令 / 并发 | main 请求/调用秒 | 候选请求/调用秒 | 配对变化 |',
          '|---|---|---:|---:|---:|']
for row in v['summary']:
    label = ' / '.join(str(row[k]) for k in ('logical_bytes', 'field_bytes', 'keys', 'layout'))
    lines.append(f'| {label} | {row["operation"]} / {row["connections"]} | {row["parent_median_client_call_rate"]:.2f} | {row["candidate_median_client_call_rate"]:.2f} | {row["client_call_rate_paired_percent"]["median"]:+.2f}% |')
lines += ['', '## 全部逐轮结果', '',
          '| 数据字节 / 成员字节 / keys / 初始分值 / 命令 / 并发 | 轮次 | QPS 变化 | p99 变化 | main 请求数 | 候选请求数 | main 调用秒数 | 候选调用秒数 | 原始记录 |',
          '|---|---:|---:|---:|---:|---:|---:|---:|---|']
for row in v['summary']:
    label = ' / '.join(str(row[k]) for k in ('logical_bytes', 'field_bytes', 'keys', 'layout', 'operation', 'connections'))
    for pair in row['pairs']:
        x, y = pair['parent'], pair['candidate']
        lines.append(f'| {label} | {pair["round"]} | {pair["qps_change_percent"]:+.2f}% | {pair["p99_change_percent"]:+.2f}% | {x["requests"]} | {y["requests"]} | {x["elapsed_seconds"]:.3f} | {y["elapsed_seconds"]:.3f} | [main](../../raw/lavik-{x["tag"]}/) / [候选](../../raw/lavik-{y["tag"]}/) |')
lines += ['', f'观测文件 SHA256：`{digest}`。', '',
          ' · '.join(f'[{label}]({path.name})' for label, path in
                     [('全部观测', a.observations), ('基数与配对核验', a.validation), ('命令计数核验', a.audit)]), '']
a.output.write_text('\n'.join(lines))
