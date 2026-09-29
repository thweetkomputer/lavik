#!/usr/bin/env python3
"""Plot the equal 256-key Hash/Set write runs for all four databases."""

import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
RUNS = {
    "Redis": "redis-1m-k256-write-20260929",
    "Valkey": "valkey-1m-k256-write-20260929",
    "Kvrocks": "kvrocks-1m-k256-write-20260929",
    "Lavik main": "lavik-main9acd-1m-k256-20260929",
}
COLORS = {"Redis": "#bd3f43", "Valkey": "#008681",
          "Kvrocks": "#a75b19", "Lavik main": "#4254b4"}
MARKERS = {"Redis": "o", "Valkey": "s", "Kvrocks": "D",
           "Lavik main": "^"}
CONNECTIONS = (80, 320, 1280, 2560, 5120)


def load():
    rows = {}
    for product, tag in RUNS.items():
        folder = ROOT / "raw" / tag
        complete = folder / "complete.json"
        if not complete.exists():
            raise RuntimeError(f"incomplete run: {folder}")
        if json.loads(complete.read_text())["failures_total"] != 0:
            raise RuntimeError(f"failed points: {folder}")
        for path in folder.glob("*.result.json"):
            row = json.loads(path.read_text())
            key = (product, row["type"], row["operation"],
                   int(row["field_bytes"]), int(row["connections"]))
            if int(row["logical_bytes"]) != 1048576 or int(row["keys"]) != 256:
                raise RuntimeError(f"unexpected workload: {path}")
            if key in rows:
                raise RuntimeError(f"duplicate point: {key}")
            rows[key] = float(row["qps"])
    expected = {(product, kind, operation, field, connection)
                for product in RUNS
                for kind, operations in (("hash", ("HGET", "HSET")),
                                         ("set", ("SISMEMBER", "SADD_SREM")))
                for operation in operations
                for field in (128, 1024)
                for connection in CONNECTIONS}
    if set(rows) != expected:
        raise RuntimeError(f"wrong point grid: missing={expected-set(rows)}, "
                           f"extra={set(rows)-expected}")
    return rows


def main():
    rows = load()
    chart_dir = ROOT / "charts"
    chart_dir.mkdir(exist_ok=True)
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False,
                         "axes.spines.right": False, "figure.facecolor": "white"})
    for kind, operation in (("hash", "HSET"), ("set", "SADD_SREM")):
        fig, axes = plt.subplots(1, 2, figsize=(12.8, 4.8))
        for ax, field in zip(axes, (128, 1024)):
            for product in RUNS:
                points = [rows[(product, kind, operation, field, connection)]
                          for connection in CONNECTIONS]
                ax.plot(CONNECTIONS, points, marker=MARKERS[product],
                        linewidth=2, color=COLORS[product],
                        label="Kvrocks (80 GiB cache)" if product == "Kvrocks"
                        else product)
            ax.set_title(f"{'128 B' if field == 128 else '1 KiB'}/entry")
            ax.set_xlabel("Connections (log scale)")
            ax.set_xscale("log")
            ax.set_yscale("log")
            ax.set_ylabel("Throughput (QPS, log scale)")
            ax.grid(alpha=0.2)
            ax.legend(fontsize=8)
        fig.suptitle(f"{kind.capitalize()} · {operation.replace('_', ' + ')} "
                     "· 1 MiB/key · 256 keys")
        fig.tight_layout()
        fig.savefig(chart_dir / f"{kind}-{operation.lower()}-1048576-k256.png",
                    dpi=150)
        plt.close(fig)
    with (ROOT / "write-256.csv").open("w", newline="") as output:
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(("product", "type", "logical_bytes", "keys",
                         "field_bytes", "operation", "connections", "qps"))
        for key, qps in sorted(rows.items()):
            product, kind, operation, field, connection = key
            if operation not in ("HSET", "SADD_SREM"):
                continue
            writer.writerow((product, kind, 1048576, 256, field, operation,
                             connection, qps))


if __name__ == "__main__":
    main()
