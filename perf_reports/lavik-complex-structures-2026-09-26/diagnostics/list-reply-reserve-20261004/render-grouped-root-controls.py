"""Render the completed, independently validated comparison without rerunning it."""

import argparse
import hashlib
import json
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observations", type=Path, required=True)
    parser.add_argument("--validation", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    observations = json.loads(args.observations.read_text())
    validation = json.loads(args.validation.read_text())
    audit = json.loads(args.audit.read_text())
    source_hash = digest(args.observations)
    # Refuse partial or mismatched snapshots before producing report text.
    assert validation["input_sha256"] == audit["input_sha256"] == source_hash
    assert validation["observations"] == audit["observations"] == 72
    assert len(observations["rows"]) == 72 and len(validation["summary"]) == 12
    assert validation["status"] == "Complete 72-point ordinary-key comparison verified"
    assert validation["versions"] == observations["versions"]
    lines = [
        "# #282 固定版本的完整 72 点普通 key 对照", "",
        "比较父版本 `19496654` 与根记录复用候选 `28d7cca4`。"
        "测量固定历史提交，不代表当前 main 或 rebase 后 head 的整体性能。", "",
        "12 个条件各执行三轮 A/B、B/A、A/B；每点 30 秒、pipeline=1。"
        "读取每轮共享父版本新建的逻辑数据，后台物理变化仍可能发生；写入分别新建数据。"
        "全部 key 基数、源码/二进制身份、构建配置、正常退出及实际命令计数已核验。", "",
        "表中绝对值是各版本三次观测的中位数；变化是三个配对百分比的中位数，"
        "两种计算不可互换。QPS 越高越好，p99 越低越好。三轮不是置信区间；"
        "逐轮请求数和结果保留在下表及 JSON。", "",
        "其他三个系统没有重跑，持久化配置也不相同；不据此宣称整体追平，"
        "Hash/Set 使用 500 keys，而非历史 50,000-key 条件，不能用于更新历史 peer 排名。", "",
        "父版本完整 CI 仍因外部 Redis cluster bus 端口冲突而失败，该导入场景不在本对照的验证范围内。"
        "两边原生回归均为 68 通过、28 个故障注入用例跳过；候选另有 128 个单元测试通过。"
        "这些短 key 控制也不等于长 key 延迟的成对测量，不解释历史 SET 超时。", "",
        "| 条件（结构 / 字节 / 成员字节 / keys） | 命令 / 并发 | 父版本 QPS | 候选 QPS | 配对 QPS 变化 | 父版本 p99 ms | 候选 p99 ms | 配对 p99 变化 |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in validation["summary"]:
        condition = " / ".join(str(row[k]) for k in ("type", "logical_bytes", "field_bytes", "keys"))
        lines.append(
            f'| {condition} | {row["operation"]} / {row["connections"]} | '
            f'{row["parent_median_qps"]:.2f} | {row["candidate_median_qps"]:.2f} | '
            f'{row["qps_paired_percent"]["median"]:+.2f}% | '
            f'{row["parent_median_p99_ms"]:.3f} | {row["candidate_median_p99_ms"]:.3f} | '
            f'{row["p99_paired_percent"]["median"]:+.2f}% |'
        )
    lines += ["", "## 逐轮变化与请求数", "",
              "保留所有轮次，包括负收益和尾延迟恶化；原始目录链接保留命令输出与 INFO 快照。", "",
              "| 条件 / 命令 / 并发 | 轮次 | QPS 变化 | p99 变化 | 父版本请求数 | 候选请求数 | 原始数据 |",
              "|---|---:|---:|---:|---:|---:|---|"]
    for row in validation["summary"]:
        label = " / ".join(str(row[k]) for k in ("type", "logical_bytes", "field_bytes", "keys", "operation", "connections"))
        for pair in row["pairs"]:
            a, b = pair["parent"], pair["candidate"]
            lines.append(
                f'| {label} | {pair["round"]} | {pair["qps_change_percent"]:+.2f}% | '
                f'{pair["p99_change_percent"]:+.2f}% | {a["requests"]} | {b["requests"]} | '
                f'[父版本](../../raw/lavik-{a["tag"]}/) / [候选](../../raw/lavik-{b["tag"]}/) |'
            )
    lines += ["", "## 可复核输入", "",
              f'观测清单 SHA256：`{source_hash}`。', "",
              " · ".join(f"[{label}]({path.name})" for label, path in (
                  ("全部观测", args.observations), ("完整校验与配对值", args.validation),
                  ("实际命令计数", args.audit))), ""]
    args.output.write_text("\n".join(lines))


if __name__ == "__main__":
    main()
