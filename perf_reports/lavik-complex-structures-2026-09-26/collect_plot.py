#!/usr/bin/env python3
"""Collect validated memtier result JSON and draw product-comparison curves."""
import csv
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
PRODUCTS = ("redis", "valkey", "lavik")
COLORS = {"redis": "#bd3f43", "valkey": "#008681", "lavik": "#3e5bc7"}
MARKERS = {"redis": "o", "valkey": "s", "lavik": "^"}
STYLES = {"redis": "-", "valkey": "--", "lavik": ":"}
OPERATIONS = {"hash": ("HGET", "HSET"), "set": ("SISMEMBER", "SADD_SREM"),
              "list": ("LINDEX", "LSET"), "zset": ("ZSCORE", "ZINCRBY"),
              "stream": ("XRANGE", "XADD_MAXLEN")}
FULL_OP = {"hash": "HGETALL", "set": "SMEMBERS", "list": "LRANGE",
           "zset": "ZRANGE", "stream": "XRANGE_FULL"}
HEADERS = ("product", "type", "logical_bytes", "field_bytes", "entries_per_key",
           "keys", "operation", "connections", "qps", "p50_ms", "p99_ms",
           "p999_ms", "requests", "elapsed_seconds", "seconds",
           "client_cpu_cores", "rx_mib_s")
rows = []
for product in PRODUCTS:
    folder = ROOT / "raw" / product
    if not folder.exists():
        continue
    for path in folder.glob("*.result.json"):
        row = json.loads(path.read_text())
        if any(key not in row for key in HEADERS
               if key not in ("client_cpu_cores", "rx_mib_s")):
            raise RuntimeError(f"incomplete result: {path}")
        stats_path = path.with_name(path.name.replace(".result.json", ".json"))
        stats = json.loads(stats_path.read_text())["ALL STATS"]
        row["client_cpu_cores"] = stats["CPU"]["cpu_cores_used"]
        row["rx_mib_s"] = stats["Totals"]["KB/sec RX"] / 1024
        rows.append(row)
rows.sort(key=lambda r: (r["type"], r["logical_bytes"], r["field_bytes"],
                         r["operation"], r["connections"], r["product"]))
identities = [(r["product"], r["type"], r["logical_bytes"],
               r["field_bytes"], r["operation"], r["connections"]) for r in rows]
if len(identities) != len(set(identities)):
    raise RuntimeError("duplicate benchmark result")
if all((ROOT / "raw" / product / "complete.json").exists()
       for product in PRODUCTS):
    expected = {(product, kind, size, field, operation, connection)
                for product in PRODUCTS for kind, operations in OPERATIONS.items()
                for size in (65536, 1048576) for field in (128, 1024)
                for operation in operations
                for connection in (80, 320, 1280, 2560, 5120)}
    expected |= {(product, kind, size, field, operation, connection)
                 for product in PRODUCTS for kind, operation in FULL_OP.items()
                 for size in (65536, 1048576) for field in (128, 1024)
                 for connection in (16, 80)}
    if set(identities) != expected:
        raise RuntimeError(f"result grid differs: missing={expected - set(identities)}, "
                           f"unexpected={set(identities) - expected}")
with (ROOT / "results.csv").open("w", newline="") as output:
    writer = csv.DictWriter(output, fieldnames=HEADERS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

if not rows:
    raise RuntimeError("no benchmark results")
plt.rcParams.update({"font.size": 11, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.facecolor": "white"})
charts = ROOT / "charts"
charts.mkdir(exist_ok=True)
for kind in OPERATIONS:
    for size in sorted({r["logical_bytes"] for r in rows if r["type"] == kind}):
        for field in sorted({r["field_bytes"] for r in rows
                             if r["type"] == kind and r["logical_bytes"] == size}):
            fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.5), sharex=True)
            for index, (ax, op) in enumerate(zip(axes, OPERATIONS[kind])):
                subset = [r for r in rows if r["type"] == kind
                          and r["logical_bytes"] == size
                          and r["field_bytes"] == field
                          and r["operation"] == op]
                for product in PRODUCTS:
                    points = sorted((r for r in subset if r["product"] == product),
                                    key=lambda r: r["connections"])
                    if points:
                        ax.plot([r["connections"] for r in points],
                                [r["qps"] / 1000 for r in points],
                                color=COLORS[product], marker=MARKERS[product],
                                linestyle=STYLES[product], linewidth=2,
                                label=product.capitalize())
                ax.set_title(op.replace("_", " + " if op == "SADD_SREM" else " "))
                ax.set_xlabel("Connections (log scale)")
                if index == 0:
                    ax.set_ylabel("Throughput (k QPS)")
                    ax.set_ylim(bottom=0)
                else:
                    ax.set_ylabel("Throughput (k QPS, log scale)")
                    ax.set_yscale("log")
                    ax.set_ylim(1, 2000)
                ax.set_xscale("log", base=2)
                ticks = sorted({r["connections"] for r in subset})
                ax.set_xticks(ticks, [str(x) for x in ticks])
                ax.grid(axis="y", alpha=0.2)
            handles, labels = axes[0].get_legend_handles_labels()
            if not handles:
                handles, labels = axes[1].get_legend_handles_labels()
            fig.legend(handles, labels, loc="upper center", ncol=3,
                       frameon=False, bbox_to_anchor=(0.5, 0.89))
            size_label = f"{size // 1048576} MiB" if size >= 1048576 else f"{size // 1024} KiB"
            field_label = f"{field // 1024} KiB" if field >= 1024 else f"{field} B"
            fig.suptitle(f"{kind.title()} | {size_label} per key | {field_label} per element",
                         y=0.99, fontsize=13, fontweight="bold")
            fig.subplots_adjust(left=0.11, right=0.98, bottom=0.17,
                                top=0.70, wspace=0.31)
            fig.savefig(charts / f"{kind}-{size}-{field}.png", dpi=150,
                        facecolor="white")
            plt.close(fig)
            full = [r for r in rows if r["type"] == kind
                    and r["logical_bytes"] == size and r["field_bytes"] == field
                    and r["operation"] == FULL_OP[kind]]
            if full:
                fig, ax = plt.subplots(figsize=(6.2, 4.2))
                for product in PRODUCTS:
                    points = sorted((r for r in full if r["product"] == product),
                                    key=lambda r: r["connections"])
                    if points:
                        ax.plot([r["connections"] for r in points],
                                [r["qps"] for r in points],
                                color=COLORS[product], marker=MARKERS[product],
                                linestyle=STYLES[product], linewidth=2,
                                label=product.capitalize())
                fig.suptitle(f"{kind.title()} | {size_label} per key | {field_label} per element",
                             y=0.99, fontsize=12, fontweight="bold")
                ax.set_title(f"Full read: {FULL_OP[kind].replace('_FULL', '')}")
                ax.set_xlabel("Connections")
                ax.set_ylabel("Throughput (QPS)")
                ax.set_ylim(bottom=0)
                ax.set_xticks((16, 80))
                ax.grid(axis="y", alpha=0.2)
                fig.legend(*ax.get_legend_handles_labels(), frameon=False,
                           ncol=3, loc="upper center", bbox_to_anchor=(0.5, 0.86))
                fig.subplots_adjust(left=0.15, right=0.96, bottom=0.17,
                                    top=0.68)
                fig.savefig(charts / f"{kind}-{size}-{field}-full.png", dpi=150,
                            facecolor="white")
                plt.close(fig)
print(f"{len(rows)} rows, {len(list(charts.glob('*.png')))} charts")
