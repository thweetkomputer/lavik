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
    assert validation["observations"] == audit["observations"] == 150
    assert len(observations["rows"]) == 150 and len(validation["summary"]) == 25
    assert validation["status"] == "Complete 150-point comparison verified"
    assert validation["versions"] == observations["versions"]
    lines = [
        "# 固定组合的完整 150 点对照", "",
        "比较 main `4610d607` 与组合 `78e29277`（#265/#266/#270 的固定历史提交）。"
        "不包含 #275/#280/#282，也不代表当前 main 的整体性能。", "",
        "25 个条件各执行三轮 A/B、B/A、A/B；每点 30 秒、pipeline=1。"
        "读取每轮共享父版本新建的逻辑数据，后台物理变化仍可能发生；写入分别新建数据。"
        "全部 key 基数、源码/二进制身份、构建配置、正常退出及实际命令计数已核验。", "",
        "表中绝对值是各版本三次观测的中位数；变化是三个配对百分比的中位数，"
        "两种计算不可互换。QPS 越高越好，p99 越低越好。三轮不是置信区间；"
        "全量读取请求数较少，逐轮请求数和结果保留在下表及 JSON。", "",
        "其他三个系统没有重跑，持久化配置也不相同；不据此宣称整体追平，"
        "也不相加或相乘各 PR 的单独收益。", "",
        "| 条件（结构 / 字节 / 成员字节 / keys） | 命令 / 并发 | main QPS | 组合 QPS | 配对 QPS 变化 | main p99 ms | 组合 p99 ms | 配对 p99 变化 |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in validation["summary"]:
        condition = " / ".join(str(row[k]) for k in ("type", "logical_bytes", "field_bytes", "keys"))
        lines.append(
            f'| {condition} | {row["operation"]} / {row["connections"]} | '
            f'{row["main_median_qps"]:.2f} | {row["combined_median_qps"]:.2f} | '
            f'{row["qps_paired_percent"]["median"]:+.2f}% | '
            f'{row["main_median_p99_ms"]:.3f} | {row["combined_median_p99_ms"]:.3f} | '
            f'{row["p99_paired_percent"]["median"]:+.2f}% |'
        )
    lines += ["", "## 逐轮变化与请求数", "",
              "保留所有轮次，包括负收益和尾延迟恶化；原始目录链接保留命令输出与 INFO 快照。", "",
              "| 条件 / 命令 / 并发 | 轮次 | QPS 变化 | p99 变化 | main 请求数 | 组合请求数 | 原始数据 |",
              "|---|---:|---:|---:|---:|---:|---|"]
    for row in validation["summary"]:
        label = " / ".join(str(row[k]) for k in ("type", "logical_bytes", "field_bytes", "keys", "operation", "connections"))
        for pair in row["pairs"]:
            a, b = pair["main"], pair["combined"]
            lines.append(
                f'| {label} | {pair["round"]} | {pair["qps_change_percent"]:+.2f}% | '
                f'{pair["p99_change_percent"]:+.2f}% | {a["requests"]} | {b["requests"]} | '
                f'[main](../../raw/lavik-{a["tag"]}/) / [组合](../../raw/lavik-{b["tag"]}/) |'
            )
    lines += ["", "## 可复核输入", "",
              f'观测清单 SHA256：`{source_hash}`。', "",
              " · ".join(f"[{label}]({path.name})" for label, path in (
                  ("全部观测", args.observations), ("完整校验与配对值", args.validation),
                  ("实际命令计数", args.audit))), ""]
    args.output.write_text("\n".join(lines))


if __name__ == "__main__":
    main()
