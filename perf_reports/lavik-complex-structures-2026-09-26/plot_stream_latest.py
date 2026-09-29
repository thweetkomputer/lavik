#!/usr/bin/env python3
"""Plot only the merged-main Stream measurements alongside peer runs."""

import argparse
import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
RUNS = {
    65536: {
        "Redis": "redis", "Valkey": "valkey", "Kvrocks": "kvrocks",
        "Lavik main": "lavik-main9acd-stream-small-20260929",
    },
    1048576: {
        "Redis": "redis", "Valkey": "valkey", "Kvrocks": "kvrocks",
        "Lavik main": "lavik-main9acd-stream-small-20260929",
    },
    104857600: {
        "Redis": "redis-100m", "Valkey": "valkey-100m",
        "Kvrocks": "kvrocks-100m",
        "Lavik main": "lavik-main9acd-stream-100m-20260929",
    },
}
COLORS = {"Redis": "#bd3f43", "Valkey": "#008681",
          "Kvrocks": "#a75b19", "Lavik main": "#2448a8"}
MARKERS = {"Redis": "o", "Valkey": "s", "Kvrocks": "D",
           "Lavik main": "^"}
POINT_LEVELS = (80, 320, 1280, 2560, 5120)
FULL_LEVELS = {65536: (16, 80), 1048576: (16, 80),
               104857600: (1, 4, 16)}
SIZES = (65536, 1048576, 104857600)
FIELDS = {65536: (128, 1024), 1048576: (128, 1024),
          104857600: (1024,)}
OPERATIONS = (("xrange", "Exact-ID XRANGE"),
              ("xadd_maxlen", "XADD MAXLEN"),
              ("xrange_full", "XRANGE - +"))


def result(product, tag, size, field, operation, connections):
    path = (ROOT / "raw" / tag /
            f"stream-{size}-{field}-{operation}-c{connections}.result.json")
    if not path.exists():
        return None
    row = json.loads(path.read_text())
    if (row["type"] != "stream" or row["logical_bytes"] != size or
            row["field_bytes"] != field or row["connections"] != connections or
            row["keys"] != (8 if size == 104857600 else 64) or
            row["seconds"] != 8 or row["product"] != tag):
        raise ValueError(f"unexpected workload in {path}")
    return float(row["qps"])


def draw(size, field, operation, title, writer):
    levels = FULL_LEVELS[size] if operation == "xrange_full" else POINT_LEVELS
    fig, ax = plt.subplots(figsize=(8, 4.7))
    for product, tag in RUNS[size].items():
        points = [result(product, tag, size, field, operation, c)
                  for c in levels]
        for c, qps in zip(levels, points):
            if qps is not None:
                writer.writerow((product, tag, size, field, operation, c, qps))
        if any(qps is None for qps in points):
            raise ValueError(f"incomplete run: {tag}, {size}, {field}, {operation}")
        ax.plot(levels, points, color=COLORS[product], marker=MARKERS[product],
                linewidth=2, markersize=5, label=product)
    ax.set_xscale("log", base=2)
    ax.set_yscale("log")
    ax.set_xticks(levels, [str(c) for c in levels])
    ax.set_xlabel("Connections")
    ax.set_ylabel("QPS")
    size_label = {65536: "64 KiB", 1048576: "1 MiB",
                  104857600: "100 MiB"}[size]
    field_label = "1 KiB" if field == 1024 else "128 B"
    ax.set_title(f"Stream {title} · {size_label}/key · {field_label}/entry")
    ax.grid(True, which="major", color="#d6dbe4", linewidth=0.6)
    ax.grid(True, which="minor", color="#ecedf1", linewidth=0.4)
    ax.legend(ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.17),
              frameon=False)
    fig.tight_layout()
    output = ROOT / "charts" / f"stream-{size}-{field}-{operation}-latest.png"
    fig.savefig(output, dpi=160, bbox_inches="tight")
    plt.close(fig)
    print(output)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sizes", default=",".join(map(str, SIZES)))
    args = parser.parse_args()
    sizes = tuple(int(value) for value in args.sizes.split(","))
    if any(size not in SIZES for size in sizes):
        raise ValueError(f"unsupported size: {sizes}")
    with (ROOT / "stream-latest.csv").open("w", newline="") as output:
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(("product", "run_tag", "logical_bytes", "field_bytes",
                         "operation", "connections", "qps"))
        for size in sizes:
            for field in FIELDS[size]:
                for operation, title in OPERATIONS:
                    draw(size, field, operation, title, writer)


if __name__ == "__main__":
    main()
