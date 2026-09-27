#!/usr/bin/env python3
"""Plot the 100 MiB Stream follow-up beside the original four products."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
CONNECTIONS = (80, 320, 1280, 2560, 5120)
SERIES = (
    ("Redis", "redis-100m", "#bd3f43", "-"),
    ("Valkey", "valkey-100m", "#008681", "-"),
    ("Lavik baseline", "lavik-100m", "#8294d2", "--"),
    ("Lavik optimized", "lavik-stream-probe-reuse", "#2448a8", "-"),
    ("Kvrocks", "kvrocks-100m", "#a75b19", "-"),
)


def points(folder, operation):
    result = []
    for connections in CONNECTIONS:
        path = (ROOT / "raw" / folder /
                f"stream-104857600-1024-{operation}-c{connections}.result.json")
        row = json.loads(path.read_text())
        assert row["logical_bytes"] == 104857600
        assert row["field_bytes"] == 1024 and row["keys"] == 8
        assert row["connections"] == connections and row["seconds"] == 8
        result.append(row["qps"])
    return result


fig, axes = plt.subplots(1, 2, figsize=(12.4, 4.7), sharex=True)
for ax, (operation, title) in zip(
    axes, (("xrange", "Exact-ID XRANGE"), ("xadd_maxlen", "XADD MAXLEN"))
):
    for label, folder, color, style in SERIES:
        ax.plot(CONNECTIONS, points(folder, operation), linestyle=style,
                color=color, marker="o", markersize=4, linewidth=2,
                label=label)
    ax.set_title(title)
    ax.set_xscale("log", base=2)
    ax.set_yscale("log")
    ax.set_xticks(CONNECTIONS, [str(c) for c in CONNECTIONS])
    ax.set_xlabel("Connections")
    ax.set_ylabel("QPS")
    ax.grid(True, which="major", color="#d6dbe4", linewidth=0.6)
    ax.grid(True, which="minor", color="#ecedf1", linewidth=0.4)
fig.legend(*axes[0].get_legend_handles_labels(), loc="lower center",
           bbox_to_anchor=(0.5, -0.035), ncol=5, frameon=False)
fig.suptitle("100 MiB Stream per key · 1 KiB field · eight keys · pipeline 1")
fig.tight_layout(rect=(0, 0.08, 1, 0.95))
output = ROOT / "charts" / "stream-104857600-1024-optimized.png"
fig.savefig(output, dpi=180, bbox_inches="tight")
print(output)
