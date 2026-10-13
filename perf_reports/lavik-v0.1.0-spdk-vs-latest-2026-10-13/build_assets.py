#!/usr/bin/env python3
# Copyright (C) 2026 EloqData Inc.
# SPDX-License-Identifier: Apache-2.0
"""Render the committed benchmark CSV in the previous report's visual style.

Requires Matplotlib 3.11.x. Run from any directory; no benchmark host, raw
devices, or executable downloads are needed to regenerate the three report figures.
"""

import csv
import hashlib
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter, MultipleLocator

ROOT = Path(__file__).resolve().parent
CONNECTIONS = [80, 160, 320, 640, 1280]
THREADS = [1, 2, 4, 8, 16]
COLORS = {"lavik-spdk": "#1473E6", "redis": "#E97827", "valkey": "#C84C8A"}
HATCHES = {"lavik-spdk": "///", "redis": "..", "valkey": "xx"}
NAMES = {"lavik-spdk": "Lavik SPDK", "redis": "Redis", "valkey": "Valkey"}
THREAD_COLORS = ["#566573", "#168F8C", "#E97827", "#7D5CC6", "#1473E6"]
THREAD_STYLES = [":", "--", "-.", (0, (3, 2)), "-"]


def read_rows():
    """Require the complete matrix, so missing configurations cannot vanish."""
    rows = list(csv.DictReader((ROOT / "results.csv").open()))
    expected = set()
    for group, systems in [("memory", ["lavik-spdk", "redis", "valkey"])]:
        for system in systems:
            for threads in THREADS if system in ["redis", "valkey"] else [16]:
                for workload in ["GET", "SET"]:
                    for connections in CONNECTIONS:
                        expected.add((group, system, threads, workload, connections))
    for workload in ["GET", "SET"]:
        for connections in CONNECTIONS:
            expected.add(("storage", "lavik-spdk", 16, workload, connections))
    observed = set()
    for row in rows:
        for key in ["server_threads", "connections", "keys", "value_bytes", "test_seconds"]:
            row[key] = int(row[key])
        for key in ["qps", "avg_ms", "p50_ms", "p99_ms", "p999_ms"]:
            row[key] = float(row[key])
            assert math.isfinite(row[key]) and row[key] > 0, row
        key = tuple(row[k] for k in ["group", "system", "server_threads", "workload", "connections"])
        assert key not in observed, key
        observed.add(key)
        assert row["value_bytes"] == 1024 and int(row["connection_errors"]) == 0
        assert row["keys"] == (10**7 if row["group"] == "memory" else 10**9)
        assert row["test_seconds"] == (30 if row["group"] == "memory" else 60)
    assert observed == expected and len(rows) == 120
    return rows


def series(rows, group, system, workload, threads=None):
    candidates = [r for r in rows if (r["group"], r["system"], r["workload"]) ==
                  (group, system, workload)]
    # Select a single I/O-thread configuration per command, then show its whole
    # connection sweep. A pointwise maximum would hide configuration changes.
    if threads is None:
        threads = max(candidates, key=lambda r: r["qps"])["server_threads"]
    return sorted((r for r in candidates if r["server_threads"] == threads),
                  key=lambda r: r["connections"])


def frame(title, subtitle, *, thread_grid=False):
    fig = plt.figure(figsize=(16, 12.1 if thread_grid else 11.7), facecolor="white")
    fig.text(.045, .955, title, fontsize=24, weight="bold", va="top")
    fig.text(.045, .91, subtitle, fontsize=14, color="#566573")
    positions = ([.09, .54, .38, .26], [.57, .54, .38, .26],
                 [.09, .13, .38, .26], [.57, .13, .38, .26]) if thread_grid else (
                 [.09, .50, .875, .28], [.09, .115, .875, .28])
    return fig, [fig.add_axes(position) for position in positions]


def style_axis(ax, title, connections, *, metric="qps", maximum=None):
    ax.set_title(title, loc="left", fontsize=18, weight="bold", pad=15)
    ax.set_axisbelow(True)
    ax.grid(axis="y", color="#DDE3E8", linewidth=.8)
    ax.spines[["top", "right"]].set_visible(False)
    for spine in ["left", "bottom"]:
        ax.spines[spine].set_color("#7B8794")
    ax.tick_params(axis="both", length=0, pad=10, labelsize=12, colors="#566573")
    ax.set_xticks(range(len(connections)), [f"{n:,}" for n in connections])
    ax.set_xlabel("Concurrent connections", fontsize=13, weight="bold", labelpad=13)
    ax.set_ylim(0, maximum)
    ax.set_ylabel("QPS" if metric == "qps" else "p99.9 latency (ms)", fontsize=12, labelpad=12)
    if metric == "qps":
        ax.yaxis.set_major_locator(MultipleLocator(200_000))
        ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value / 1000:g}k"))


def save(fig, name, footer):
    fig.text(.045, .032, footer, fontsize=11.5, color="#566573")
    for extension in ["svg", "png"]:
        # Omit wall-clock metadata and fix SVG IDs for reproducible review diffs.
        fig.savefig(ROOT / f"{name}.{extension}", dpi=150,
                    metadata={"Date": None} if extension == "svg" else {})
        if extension == "svg":
            path = ROOT / f"{name}.svg"
            path.write_text("\n".join(line.rstrip() for line in path.read_text().splitlines()) + "\n")
    plt.close(fig)


def combined_comparison(rows, metric="qps"):
    throughput = metric == "qps"
    specs = [
        ("memory", "lavik-spdk", "Lavik v0.1.0 · 10M keys · 16 workers", "#1473E6", "///"),
        ("storage", "lavik-spdk", "Lavik v0.1.0 · 1B keys · 16 workers", "#168F8C", "\\\\"),
        ("memory", "redis", "Redis 8.10.2 · 10M keys · 16 I/O threads", "#E97827", ".."),
        ("memory", "valkey", "Valkey 9.1.2 · 10M keys · GET 16 / SET 8 I/O threads", "#C84C8A", "xx"),
    ]
    fig, axes = frame("Lavik 10M / 1B keys versus Redis and Valkey" if throughput else
                      "p99.9 latency · Lavik 10M / 1B, Redis and Valkey",
                      "1 KiB values · 16 memtier threads · pipeline 1 · Lavik SPDK / peers in DRAM")
    selected = {(group, system, workload): series(rows, group, system, workload)
                for group, system, *_ in specs for workload in ["GET", "SET"]}
    peak = max(r[metric] for values in selected.values() for r in values)
    maximum = math.ceil(peak / 200_000) * 200_000 if throughput else math.ceil(peak / 2) * 2
    markers = ["o", "s", "^", "D"]
    styles = ["-", "--", "-.", ":"]
    handles = [Patch(facecolor=color, edgecolor="white", hatch=hatch, label=label)
               if throughput else Line2D([], [], color=color, marker=markers[i],
                                        linestyle=styles[i], linewidth=2.6, label=label)
               for i, (_, _, label, color, hatch) in enumerate(specs)]
    fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(.52, .885), ncol=2,
               frameon=False, fontsize=11.5, handlelength=2.6, columnspacing=2.7)
    for ax, workload in zip(axes, ["GET", "SET"]):
        style_axis(ax, workload + (" throughput" if throughput else " p99.9 latency"),
                   CONNECTIONS, metric=metric, maximum=maximum)
        for index, (group, system, _, color, hatch) in enumerate(specs):
            values = selected[group, system, workload]
            assert [r["connections"] for r in values] == CONNECTIONS
            if throughput:
                ax.bar([x + (index - 1.5) * .20 for x in range(len(CONNECTIONS))],
                       [r[metric] for r in values], width=.18, color=color,
                       edgecolor="white", linewidth=.5, hatch=hatch)
            else:
                ax.plot(CONNECTIONS, [r[metric] for r in values], color=color,
                        marker=markers[index], linestyle=styles[index], linewidth=2.6,
                        markersize=7, markeredgecolor="white", markeredgewidth=.6)
        if throughput:
            ax.set_xlim(-.55, len(CONNECTIONS) - .45)
        else:
            ax.set_xscale("log", base=2)
            ax.set_xticks(CONNECTIONS, [f"{n:,}" for n in CONNECTIONS])
            ax.set_xlim(70, 1460)
            ax.set_xlabel("Concurrent connections (log₂ scale)", fontsize=13, weight="bold", labelpad=13)
            ax.yaxis.set_major_locator(MultipleLocator(2))
    save(fig, "combined-qps" if throughput else "combined-p999", "10M: 30 s, default client seeds · 1B: 60 s, distinct client seeds · Lavik defrag enabled · single run per point")


def peak_summary(rows):
    specs = [("memory", "lavik-spdk", "Lavik 0.1.0 SPDK", "10M", "#1473E6"),
             ("storage", "lavik-spdk", "Lavik 0.1.0 SPDK", "1B", "#168F8C"),
             ("memory", "redis", "Redis 8.10.2", "10M", "#E97827"),
             ("memory", "valkey", "Valkey 9.1.2", "10M", "#C84C8A")]
    cells = []
    colors = []
    for workload in ["GET", "SET"]:
        for group, system, label, keys, color in specs:
            point = max(series(rows, group, system, workload), key=lambda r: r["qps"])
            cells.append([workload, label, keys, str(point["server_threads"]),
                          f'{point["connections"]:,}', f'{point["qps"]:,.0f}',
                          *[f'{point[k]:.3f}' for k in ["avg_ms", "p50_ms", "p99_ms", "p999_ms"]]])
            colors.append(color)
    fig = plt.figure(figsize=(17, 6.8), facecolor="white")
    fig.text(.035, .94, "Peak throughput and its measured latency", fontsize=24, weight="bold")
    fig.text(.035, .875, "Lavik 10M / 1B keys · Redis / Valkey 10M keys · 1 KiB values · latency in milliseconds", fontsize=13, color="#566573")
    ax = fig.add_axes([.03, .24, .94, .57]); ax.axis("off")
    table = ax.table(cellText=cells,
                     colLabels=["Command", "System", "Keys", "Threads¹", "Connections", "QPS", "Avg ms", "p50 ms", "p99 ms", "p99.9 ms"],
                     colWidths=[.075, .19, .05, .072, .105, .105, .078, .075, .075, .075],
                     cellLoc="right", colLoc="right", bbox=[0, 0, 1, 1])
    table.auto_set_font_size(False); table.set_fontsize(11.5)
    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor("white"); cell.set_linewidth(1.5)
        cell.PAD = .09
        if row == 0:
            cell.set_facecolor("#17202A"); cell.get_text().set_color("white"); cell.get_text().set_weight("bold")
        else:
            cell.set_facecolor("#EDF3F8" if row <= 4 else "#F4F5F7")
            if col in [1, 2]:cell.get_text().set_color(colors[row-1]); cell.get_text().set_weight("bold")
            if col == 5:cell.get_text().set_weight("bold")
        if col in [0, 1, 2]:cell.get_text().set_ha("left")
    fig.text(.035, .165, "Each row is the measured peak QPS point for that system, dataset and command; latency comes from the same point.", fontsize=11.5, color="#566573")
    fig.text(.035, .115, "¹ Lavik: data workers; Redis / Valkey: I/O threads. Single run per point; Lavik defrag enabled.", fontsize=11.5, color="#566573")
    save(fig, "peak-summary", "10M: 30 s, default client seeds · 1B: 60 s, distinct client seeds")


def main():
    """Validate the committed rows and regenerate SVG/PNG report assets."""
    plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": "#17202A",
                         "axes.labelcolor": "#17202A", "svg.fonttype": "none",
                         "svg.hashsalt": "lavik-release010-20261013", "hatch.linewidth": .8})
    rows = read_rows()
    combined_comparison(rows)
    combined_comparison(rows, "p999_ms")
    peak_summary(rows)
    (ROOT / "chart-SHA256SUMS").write_text("".join(
        hashlib.file_digest(path.open("rb"), "sha256").hexdigest() + "  " + path.name + "\n"
        for path in sorted(ROOT.iterdir()) if path.suffix in [".svg", ".png"]))
    print("Validated 120 rows; rendered three report figures as SVG and PNG")


if __name__ == "__main__":
    main()
