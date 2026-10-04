#!/usr/bin/env python3
"""Render current four-product comparisons from explicit measured-run selection."""
import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

ROOT = Path(__file__).resolve().parent
POINT = [80, 320, 1280, 2560, 5120]
OPS = {"hash": ["HGET", "HSET", "HGETALL"],
       "set": ["SISMEMBER", "SADD_SREM", "SMEMBERS"],
       "list": ["LINDEX", "LSET", "LRANGE"],
       "zset": ["ZSCORE", "ZINCRBY", "ZRANGE"],
       "stream": ["XRANGE", "XADD_MAXLEN", "XRANGE_FULL"]}
NAMES = {"hash": "Hash", "set": "Set", "list": "List", "zset": "Sorted Set", "stream": "Stream"}
COMMANDS = {"SADD_SREM": "SADD + SREM", "LRANGE": "LRANGE 0 -1",
            "ZRANGE": "ZRANGE 0 -1 WITHSCORES", "XADD_MAXLEN": "XADD MAXLEN ~",
            "XRANGE_FULL": "XRANGE - +", "XRANGE": "XRANGE (one ID)"}
STYLES = [("#bd3f43", "o", "-"), ("#008681", "s", "--"),
          ("#a75b19", "D", "-."), ("#6574bc", "^", "-"),
          ("#7b4d9f", "v", ":"), ("#556b2f", "X", "--")]


def key(row):
    return f"{row['kind']}-{row['size']}-{row['field']}-k{row['keys']}"


def commands(row):
    return ["LSET"] if row["category"] == "lset" else OPS[row["kind"]]


def levels(row, op):
    if op == OPS[row["kind"]][-1] and row["category"] != "lset":
        return [1, 4, 16] if row["size"] == 104857600 else [16, 80]
    return POINT


def folder(product, tag):
    return ROOT / "raw" / (product + ("-" + tag if tag else ""))


def series(row):
    for product, label in [("redis", "Redis"), ("valkey", "Valkey"),
                            ("kvrocks", "Kvrocks (80 GiB cache)")]:
        if row["category"] == "hashset":
            tag = (f"{row['kind']}-{'100m' if row['size'] == 104857600 else '1m'}"
                   f"-k{row['keys']}-f{row['field']}-20260929")
        elif row["category"] == "lset":
            tag = next(p["tag"] for p in row["peers"] if p["product"] == product)
        else:
            tag = "100m" if row["size"] == 104857600 else ""
        yield label, folder(product, tag), None
    for i, revision in enumerate([row["main"], *row.get("variants", [])]):
        label = "Lavik main" if i == 0 else revision["label"]
        if i == 0 and not revision.get("fresh"):
            label = "Lavik (previous measurement)"
        yield label + " " + revision["commit"][:8], folder("lavik", revision["tag"]), revision


def load(row, source, revision):
    if not (source / "complete.json").exists():
        raise ValueError(f"incomplete run: {source}")
    if revision and revision.get("fresh"):
        complete = json.loads((source / "complete.json").read_text())
        if complete["failures_total"] != len(list(source.glob("*.error.json"))):
            raise ValueError(f"inconsistent failure inventory: {source}")
        if (source / "resume.json").exists():
            resumed = json.loads((source / "resume.json").read_text())
            if resumed["source_commit"] != revision["commit"] or resumed["sha256"] != revision["sha256"] or not resumed["retained_seed"]:
                raise ValueError(f"inconsistent resumed source: {source}")
        proofs = list(source.glob("provenance-*.json"))
        if len(proofs) != 1:
            raise ValueError(f"ambiguous source proof: {source}")
        proof = json.loads(proofs[0].read_text())
        expected = {"source_commit": revision["commit"], "sha256": revision["sha256"],
                    "types": [row["kind"]], "sizes": [row["size"]],
                    "fields": [row["field"]], "keys": row["keys"],
                    "seconds": 10 if row["category"] == "lset" else 8,
                    "mode": "point" if row["category"] == "lset" else "both",
                    "levels": POINT}
        if row["category"] != "lset":
            expected["full_levels"] = levels(row, OPS[row["kind"]][-1])
        for name, value in expected.items():
            if proof.get(name) != value:
                raise ValueError(f"{source}: {name} differs from manifest")
        if json.loads((source / "server-exit.json").read_text())["code"] != 0:
            raise ValueError(f"unclean exit: {source}")
        for stage in ("validated", "after"):
            counts = json.loads((source / f"{row['kind']}-{row['size']}-{row['field']}.{stage}.json")
                                .read_text())["sample_cardinalities"]
            delta = (100 if row["kind"] == "stream" else 1 if row["kind"] == "set" else 0) if stage == "after" else 0
            if len(counts) != row["keys"] or any(abs(n - row["size"] // row["field"]) > delta for n in counts.values()):
                raise ValueError(f"invalid key/cardinality validation: {source}")
    results, errors = {}, {}
    prefix = f"{row['kind']}-{row['size']}-{row['field']}-"
    for suffix, target in [("result", results), ("error", errors)]:
        for path in source.glob(prefix + f"*.{suffix}.json"):
            data = json.loads(path.read_text())
            point = (data["operation"], data["connections"])
            if point[0] not in commands(row):
                continue
            if point in results or point in errors:
                raise ValueError(f"duplicate/conflicting point: {path}")
            if suffix == "result":
                for name, expected in [("type", row["kind"]), ("logical_bytes", row["size"]),
                                       ("field_bytes", row["field"]), ("keys", row["keys"]),
                                       ("seconds", 10 if row["category"] == "lset" else 8)]:
                    if data.get(name) != expected:
                        raise ValueError(f"{path}: mismatched {name}")
            target[point] = data
    expected = {(op, n) for op in commands(row) for n in levels(row, op)}
    if results.keys() | errors.keys() != expected:
        raise ValueError(f"{source}: incomplete grid {expected - (results.keys() | errors.keys())}")
    return results, errors


def picture(row, op):
    return "charts/" + key(row) + "-" + op.lower() + "-current.png"


def draw(row):
    datasets = [(label, load(row, source, revision)) for label, source, revision in series(row)]
    records = []
    for op in commands(row):
        xs = levels(row, op)
        fig, ax = plt.subplots(figsize=(9, 5))
        for i, (label, (values, errors)) in enumerate(datasets):
            color, marker, style = STYLES[i % len(STYLES)]
            ys = [values[(op, n)]["qps"] if (op, n) in values else float("nan") for n in xs]
            ax.plot(xs, ys, label=label, color=color, marker=marker, linestyle=style,
                    linewidth=1.8, markersize=8 if i == 0 else 6,
                    markerfacecolor="none" if i == 0 else color, zorder=5 if i == 0 else 3)
            failed = [n for n in xs if (op, n) in errors]
            if failed:
                ax.text(.98, .025 + .055 * i, f"{label}: failed at {failed}",
                        transform=ax.transAxes, ha="right", fontsize=8)
            for n in xs:
                data = values.get((op, n), {})
                records.append({"series": label, "command": op, "connections": n,
                                "qps": data.get("qps", ""), "p99_ms": data.get("p99_ms", ""),
                                "error": errors.get((op, n), {}).get("error", "")})
        ax.set_xscale("log")
        ax.set_xticks(xs, [f"{n:,}" for n in xs])
        ax.set_xlabel("Connections (log scale)")
        write = op in ["HSET", "SADD_SREM", "LSET", "ZINCRBY", "XADD_MAXLEN"]
        if write:
            ax.set_yscale("log")
        else:
            ax.set_ylim(bottom=0)
        ax.set_ylabel("Throughput (QPS, log scale)" if write else "Throughput (QPS)")
        ax.yaxis.set_major_formatter(FuncFormatter(lambda n, _: f"{n/1000000:g}M" if n >= 1e6 else f"{n/1000:g}k" if n >= 1000 else f"{n:g}"))
        ax.grid(alpha=.20)
        ax.legend(fontsize=8, loc="best")
        size = f"{row['size']/1048576:g} MiB" if row["size"] >= 1048576 else f"{row['size']//1024} KiB"
        ax.set_title(f"{NAMES[row['kind']]} · {COMMANDS.get(op, op)}\n{size}/key · {row['keys']:,} keys · {row['field']} B/entry")
        fig.tight_layout()
        fig.savefig(ROOT / picture(row, op), dpi=150)
        plt.close(fig)
    with (ROOT / (key(row) + "-current.csv")).open("w", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=list(records[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)


def draw_list_fill(row):
    measured = []
    for label, source, revision in series(row):
        proof = json.loads(next(source.glob("provenance-*.json")).read_text())
        for name, value in {"fill_workers": 32, "seed_pipeline": 4, "seed_command_bytes": 131072}.items():
            if proof.get(name) != value:
                raise ValueError(f"{source}: unmatched RPUSH {name}")
        fill = json.loads((source / f"list-{row['size']}-{row['field']}.fill.json").read_text())
        if fill.get("command") != "RPUSH" or fill.get("client_encoding") != "shared-list-operands-v1" or fill.get("entries_per_command") != 128 or fill["commands"] != row["keys"] * (row["size"] // row["field"] // 128):
            raise ValueError(f"{source}: unmatched RPUSH client workload")
        measured.append({"series": label, "seconds": fill["seconds"], "source": str(source.relative_to(ROOT)), "source_commit": revision["commit"] if revision else ""})
    fig, ax = plt.subplots(figsize=(9.2, 4.8))
    maximum = max(r["seconds"] for r in measured)
    bars = ax.barh([r["series"] for r in measured], [r["seconds"] for r in measured], color=[STYLES[i][0] for i in range(len(measured))])
    ax.invert_yaxis()
    ax.set_xlim(0, maximum * 1.2)
    ax.set_xlabel("RPUSH fill time (seconds; lower is better)")
    ax.set_title(f"List · {row['size']//1048576} MiB/key · {row['keys']:,} keys · 1024 B/entry")
    ax.grid(axis="x", alpha=.2)
    for bar, record in zip(bars, measured):
        ax.text(record["seconds"] + maximum * .02, bar.get_y() + bar.get_height()/2, f"{record['seconds']:.1f} s", va="center")
    fig.text(.5, .01, "32 clients · 128 entries/command · pipeline 4 · persistence settings differ", ha="center", fontsize=9)
    fig.tight_layout(rect=(0, .05, 1, 1))
    fig.savefig(ROOT / "charts" / (key(row) + "-rpush-fill-current.png"), dpi=150)
    plt.close(fig)
    with (ROOT / (key(row) + "-rpush-fill-current.csv")).open("w", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(measured[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(measured)


def readme(manifest, zh):
    rows = manifest["plots"]
    done = sum(r["main"].get("fresh", False) for r in rows)
    commit = manifest["target_main"][:8]
    title = "复杂数据结构性能：Redis、Valkey、Kvrocks 与 Lavik" if zh else "Complex structures: Redis, Valkey, Kvrocks and Lavik"
    lines = ["# " + title, "", "[English](README.md)" if zh else "[简体中文](README.zh-CN.md)", ""]
    lines += [f"**2026-10-04：main `{commit}` 已完成 {done}/{len(rows)} 组复测，包含已合并的 #244、#246、#247。**" if zh else f"**2026-10-04: main `{commit}`, including merged #244/#246/#247; {done}/{len(rows)} conditions refreshed.**", ""]
    imports = json.loads((ROOT / "current-imports.json").read_text())["plots"]
    imported = sum(r["main"].get("fresh", False) for r in imports)
    import_status = f"批量 HSET/SADD 导入另计：{imported}/{len(imports)} 组已更新。" if zh else f"Batched HSET/SADD import is tracked separately: {imported}/{len(imports)} conditions refreshed."
    if imported != len(imports):
        import_status += "未完成的图注明实际历史版本。" if zh else " Pending charts identify their actual historical version."
    lines += [import_status, ""]
    lines += [("吞吐图固定命令、每 key 的 payload 大小、元素大小和 key 数；横轴为连接数，纵轴为 QPS。批量导入图显示完成固定数据量所需的秒数。只保留当前 main 和后续未合并 PR，其他三库保留同负载的历史实测。" if zh else "Throughput figures fix the command, payload bytes per key, entry size and key count; axes show connections and QPS. Batched-import figures show seconds to fill a fixed dataset. Keep the current main and subsequent unmerged PRs; peers retain historical measurements of the same workload."), ""]
    if done != len(rows):
        lines += ["未完成复测的图暂时保留带实际版本号的历史 Lavik 测量，图注明确标记待更新。旧结果没有改名为新 main。" if zh else "Pending conditions retain explicitly labeled historical Lavik measurements. Old observations are not relabeled as the new main.", ""]
    lines += ["Redis/Valkey 关闭持久化；Kvrocks 使用无压缩 RAID0、关闭 WAL、80 GiB block/blob cache；Lavik 使用六块 NVMe SPDK 持久化，不缓存字段或页内容。配置不同，写入 QPS 不代表同等持久性下的排名。" if zh else "Redis/Valkey disable persistence. Kvrocks uses uncompressed RAID0, disabled WAL and 80 GiB block/blob cache. Lavik persists through six SPDK NVMe devices without caching field/page payloads. Write QPS compares these configurations, not equivalent durability.", ""]
    lines += ["本轮不重跑其他三库。Lavik 使用 AMD EPYC 9V74、16 vCPU、12 个服务 worker。每点 8 秒，较多 key 的 LSET 为 10 秒；pipeline=1。每组独立预置并逐 key 校验，perf 采样在完整连接扫描后单独进行，不混入 QPS 图。单次扫描没有统计置信区间。" if zh else "Peers are not rerun this round. Lavik uses AMD EPYC 9V74, 16 vCPUs and 12 serving workers. Points last 8 s (10 s for high-key-count LSET), pipeline=1. Each condition is independently seeded and checked key by key. CPU profiles run separately after complete clean grids. Single sweeps have no statistical confidence intervals.", ""]
    lines += ["复测期间 #248（FDS/Meta 发现）及 #245（CI 分片）合入 main `25e15941`，代码、报告与 PR #249 已同步 rebase。本轮单机实验固定使用 main `5d7d12ec` 和 PR `97f81cd6` 的已验证二进制，图中提交号保持实际测量版本；存储源码在这次 rebase 前后一致。[版本核验](diagnostics/main-refresh-20261004/fds-rebase-provenance.json)。" if zh else "FDS/Meta discovery fix #248 and CI sharding #245 merged into main `25e15941` during measurement; the checkout, report and PR #249 are rebased. This standalone experiment keeps its verified main `5d7d12ec` and PR `97f81cd6` binaries and actual measured commit labels. Storage sources are unchanged across this rebase. [Revision verification](diagnostics/main-refresh-20261004/fds-rebase-provenance.json).", ""]
    lines += ["[绘图数据清单](current-main.json) · [复现脚本](run.py) · [构建与硬件证明](diagnostics/main-refresh-20261004/host-and-build.json)" if zh else "[Plot sources](current-main.json) · [Runner](run.py) · [Build and hardware](diagnostics/main-refresh-20261004/host-and-build.json)", ""]
    if (ROOT / "diagnostics/main-refresh-20261004/report-audit.json").exists():
        lines += ["[绘图数据核验结果](diagnostics/main-refresh-20261004/report-audit.json) · [核验脚本](diagnostics/main-refresh-20261004/audit-report.py)" if zh else "[Plot-data audit](diagnostics/main-refresh-20261004/report-audit.json) · [Audit script](diagnostics/main-refresh-20261004/audit-report.py)", ""]
    lines += ["[Hash/Set 写入 perf 分析](diagnostics/hashset-write-20261004/README.md) · [有序目录优化与测试](diagnostics/ordered-metadata-20261004/README.md)" if zh else "[Hash/Set write profiles](diagnostics/hashset-write-20261004/README.md) · [Ordered metadata optimization and tests](diagnostics/ordered-metadata-20261004/README.md)", ""]
    active = {v["pr"]: v["url"] for r in rows for v in r.get("variants", []) if "pr" in v}
    if active:
        links = " · ".join(f"[PR #{number}]({url})" for number, url in sorted(active.items()))
        lines += [("未合并优化：" if zh else "Unmerged optimizations: ") + links, ""]
    if 249 in active:
        lines += ["PR #249 的实测：Stream XADD MAXLEN 两组峰值提高约 9%–11%；100 MiB × 500 key 的 RPUSH 导入耗时减少约 20.7%。LSET 没有测到提升，100 MiB 组峰值低 3.3%。这些是单次扫描结果，仍未达到 Kvrocks 的写入吞吐。[原始比较与限制](diagnostics/ordered-metadata-20261004/README.md)。" if zh else "PR #249 measurements: Stream XADD MAXLEN peaks improve by about 9%–11% in two conditions; RPUSH fill time for 500 keys of 100 MiB falls by about 20.7%. LSET shows no improvement, with its 100 MiB peak 3.3% lower. These are single sweeps and do not reach Kvrocks write throughput. [Comparisons and limitations](diagnostics/ordered-metadata-20261004/README.md).", ""]
    failures = []
    resumes = []
    for row in rows:
        if not row["main"].get("fresh"):
            continue
        source = folder("lavik", row["main"]["tag"])
        for path in sorted(source.glob("*.error.json")):
            failure = json.loads(path.read_text())
            label = f"{NAMES[row['kind']]} {failure['operation']} · {row['size']//1048576} MiB/key · {row['field']} B · {failure['connections']} connections"
            failures.append(f"- {label}: [recorded failure]({path.relative_to(ROOT)}).")
        if (source / "resume.json").exists():
            resumes.append(f"[{NAMES[row['kind']]} {row['size']//1048576} MiB / {row['field']} B]({(source/'resume.json').relative_to(ROOT)})")
    if failures:
        lines += ["本轮失败测点（图中留空，错误请求的吞吐不计为成功 QPS）：" if zh else "Failed observations in this run (gaps in figures; errored requests are not successful QPS):", "", *failures, ""]
    if any(row["kind"] == "list" and row["size"] == 104857600 and row["field"] == 128 and row["main"].get("fresh") for row in rows):
        lines += ["[100 MiB LRANGE 内存准入分析](diagnostics/main-refresh-20261004/list-lrange-admission.md)" if zh else "[100 MiB LRANGE admission analysis](diagnostics/main-refresh-20261004/list-lrange-admission.md)", ""]
    if resumes:
        lines += [("以下扫描在正常停服后恢复同一份数据继续，只补缺失点，成功和失败的已有观察均保留：" if zh else "These grids resume the same retained dataset after a clean stop, measuring only missing points and retaining all existing successes/failures: ") + " · ".join(resumes) + ".", ""]
    for kind in ["list", "hash", "set", "zset", "stream"]:
        lines += ["## " + NAMES[kind], ""]
        if kind == "set":
            lines += ["SADD + SREM 为两个命令等比例混合，QPS 计算完成的命令数，不是命令对数。随机命中相同 key 时可能产生空操作，因此不代表实际持久化修改次数。" if zh else "SADD + SREM mixes the two commands equally; QPS counts commands, not pairs. Random concurrent access can produce no-op additions/removals, so this is not the rate of durable changes.", ""]
        for op in OPS[kind]:
            lines += ["### " + COMMANDS.get(op, op), ""]
            selected = [r for r in rows if r["kind"] == kind and op in commands(r)]
            if op == "LSET":
                # Replace only matched size/entry workloads. Keep 128-byte
                # comparisons whose expanded-key peer runs do not exist.
                replaced = {(r["size"], r["field"]) for r in selected if r["category"] == "lset"}
                selected = [r for r in selected if r["category"] == "lset" or (r["size"], r["field"]) not in replaced]
            for size in sorted({r["size"] for r in selected}):
                size_label = f"{size//1048576} MiB/key" if size >= 1048576 else f"{size//1024} KiB/key"
                lines += ["#### " + size_label, ""]
                for r in sorted((r for r in selected if r["size"] == size), key=lambda x: (x["field"], x["keys"])):
                    status = ("本轮 main 基线" if zh else "Measured main baseline") if r["main"].get("fresh") else ("历史测量，待复测" if zh else "Historical measurement; refresh pending")
                    desc = f"{r['field']} B/entry · {r['keys']:,} keys · {status} `{r['main']['commit'][:8]}`"
                    lines += [desc, "", f"![{NAMES[kind]} {op} {size_label}, {r['field']} B, {r['keys']} keys]({picture(r, op)})", ""]
                    links = [f"[{label}]({source.relative_to(ROOT)}/)" for label, source, _ in series(r)]
                    lines += [" · ".join(links), ""]
        if kind == "list":
            lines += ["### RPUSH " + ("批量预置" if zh else "batched seeding"), "", "与 LSET 使用同一组独立预置计时：32 客户端、pipeline=4、每命令 128 个 1 KiB 元素，四库使用相同的客户端编码。" if zh else "Independent LSET seeding timings: 32 clients, pipeline=4, 128 one-KiB entries per command, with the same client encoder across all four databases.", ""]
            for r in (r for r in rows if r["category"] == "lset"):
                lines += [f"#### {r['size']//1048576} MiB/key", "", f"![List RPUSH fill, {r['keys']} keys](charts/{key(r)}-rpush-fill-current.png)", ""]
        if kind in ("hash", "set"):
            imports = json.loads((ROOT / "current-imports.json").read_text())["plots"]
            command = "HSET" if kind == "hash" else "SADD"
            lines += ["### " + command + (" 批量导入" if zh else " batched import"), "", "#### 1 MiB/key", ""]
            lines += ["50,000 keys；8 个客户端、pipeline=64、每命令约 16 KiB 元素。使用与历史三库相同的逐命令 RESP 编码方式，耗时包含 Python 客户端编码；不是 RESTORE，也不代表数据库单独的吞吐上限。" if zh else "50,000 keys; 8 clients, pipeline=64, about 16 KiB entries/command. Per-command RESP encoding matches the historical peer workload; elapsed time includes Python client encoding. This is not RESTORE or a server-only throughput ceiling.", ""]
            for item in (r for r in imports if r["kind"] == kind):
                version = item["main"]
                status = ("本轮 main 基线" if zh else "Measured main baseline") if version.get("fresh") else ("历史测量，导入复测待完成" if zh else "Historical measurement; import refresh pending")
                lines += [f"{item['field']} B/entry · {status} `{version['commit'][:8]}`", "", f"![{command} batched import, {item['field']} B](charts/{kind}-1048576-{item['field']}-k50000-fill.png)", "", f"[Lavik raw](raw/lavik-{version['tag']}/)", ""]
    lines += ["## " + ("测量与复现" if zh else "Measurement and reproduction"), ""]
    lines += ["memtier 在独立客户端主机 172.16.0.5 上运行，绑定 CPU 0–15；key 均匀随机。HGET/HSET、SISMEMBER、LINDEX/LSET、ZSCORE/ZINCRBY 和指定 ID 的 XRANGE 在每 key 的八个等距位置间轮换，并非对所有字段均匀采样。SADD/SREM 使用固定测试 member；XADD MAXLEN 追加新 ID。每组按连接数顺序测试，后续写入点继承前面测点改变的值和布局。" if zh else "memtier runs on the separate client 172.16.0.5 pinned to CPUs 0–15, with uniformly random keys. HGET/HSET, SISMEMBER, LINDEX/LSET, ZSCORE/ZINCRBY and one-ID XRANGE rotate through eight evenly spaced positions per key, not all fields uniformly. SADD/SREM uses a fixed test member; XADD MAXLEN appends new IDs. Connection points run sequentially within a condition, so later writes inherit values/layout changed by earlier points.", ""]
    lines += ["Hash/Set：1 MiB/key 使用 50,000 keys，100 MiB/key 使用 500 keys。LSET 的大 key 数负载同样使用 50,000/500 keys。其他有序结构保留既有四库一致的 64/8-key 负载，标题明确区分；不同 key 数的曲线不能直接比较。" if zh else "Hash/Set use 50,000 keys at 1 MiB/key and 500 at 100 MiB/key; high-key-count LSET uses the same counts. Other ordered-structure conditions retain the matched 64/8-key peer workloads, explicitly identified in titles. Different key counts are not interchangeable.", ""]
    lines += ["Hash/Set 以 RESTORE 独立预置后清理、重启恢复再测；LSET 大 key 数预置使用 32 个连接、128 KiB RPUSH 批次、pipeline=4。预置耗时保存在每组 raw 目录中，不将 RESTORE 与其他系统的 HSET/SADD 导入耗时混比。" if zh else "Hash/Set use independent RESTORE seeding, transaction cleanup and recovery before measurement. High-key-count LSET seeds with 32 clients, 128 KiB RPUSH batches and pipeline=4. Fill timings remain in raw directories; RESTORE timings are not equated with peer HSET/SADD import timings.", ""]
    lines += ["读取整个 100 MiB key 的低吞吐测点可能只有少量完成回复，小差异不作性能结论。八秒成功不代表长时间高并发下内存稳定；历史 SMEMBERS 持续负载曾触发内存准入拒绝。失败测点保留断线与说明，不填零、不插值。" if zh else "Low-throughput whole-key reads can complete few replies in eight seconds; small differences are not performance conclusions. Eight successful seconds do not establish sustained memory stability: an earlier sustained SMEMBERS run exhausted memory admission. Failed points remain gaps with annotations, never zeroes or interpolated values.", ""]
    lines += ["历史优化数据保存在 `raw/` 和 `diagnostics/`，不再显示为已合并 PR 的独立曲线。" if zh else "Historical optimization evidence remains in raw/ and diagnostics/; merged PRs are not shown as separate series.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--condition", help="Render one condition ID; otherwise all")
    args = parser.parse_args()
    manifest = json.loads((ROOT / "current-main.json").read_text())
    for row in manifest["plots"]:
        if args.condition is None or key(row) == args.condition:
            draw(row)
    for row in manifest["plots"]:
        if row["category"] == "lset" and (args.condition is None or key(row) == args.condition or not (ROOT / "charts" / (key(row) + "-rpush-fill-current.png")).exists()):
            draw_list_fill(row)
    imports_path = ROOT / "current-imports.json"
    imports = json.loads(imports_path.read_text())
    for item in imports["plots"]:
        v = item["main"]
        if item.get("chart_commit") == v["commit"] and item.get("chart_tag") == v["tag"]:
            continue
        label = ("Lavik main " if v.get("fresh") else "Lavik (previous measurement) ") + v["commit"][:8]
        subprocess.run([sys.executable, str(ROOT / "plot_fill_reference.py"), item["kind"], "--size", str(item["size"]), "--field", str(item["field"]), "--lavik-tag", v["tag"], "--lavik-commit", v["commit"], "--lavik-sha256", v["sha256"], "--lavik-label", label], check=True)
        item["chart_commit"] = v["commit"]
        item["chart_tag"] = v["tag"]
    imports_path.write_text(json.dumps(imports, indent=2) + "\n")
    for zh, name in [(True, "README.zh-CN.md"), (False, "README.md")]:
        (ROOT / name).write_text(readme(manifest, zh))


if __name__ == "__main__":
    main()
