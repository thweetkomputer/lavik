#!/usr/bin/env python3
"""Collect validated memtier sweep rows into the chart's reviewable CSV."""

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"
FIELDS = ("size_bytes", "operation", "connections", "product", "qps",
          "p99_ms", "source")


def load(directory, product):
    for path in sorted((RAW / directory).glob("*.result.json")):
        data = json.loads(path.read_text())
        if data["kind"] not in ("GET", "SET") or "connections" not in data:
            continue
        yield {
            "size_bytes": data["size"], "operation": data["kind"],
            "connections": data["connections"], "product": product,
            "qps": data["qps"], "p99_ms": data["p99_ms"],
            "source": directory,
        }


def main():
    rows = {}
    # Later directories intentionally replace only overlapping points. The
    # Valkey 128 KiB repeat replaces the anomalous first run at every level.
    for directory, product in (
        ("redis", "Redis"), ("valkey", "Valkey"),
        ("valkey-repeat128", "Valkey"),
        ("valkey-verified128", "Valkey"),
        ("valkey-high2k", "Valkey"),
        ("lavik-baseline", "Lavik"), ("lavik-serial", "Lavik serial"),
        ("lavik-parallel", "Lavik"), ("lavik-high", "Lavik"),
        ("redis-1m-20260926", "Redis"),
        ("valkey-1m-20260926", "Valkey"),
        ("lavik-baseline1m-20260926", "Lavik before cleaner"),
        ("lavik-parallelcleaner1m-20260926", "Lavik"),
        ("lavik-final1m-20260926", "Lavik"),
    ):
        for row in load(directory, product):
            # The final read sweep replaces the baseline GET points in the
            # Lavik series; only SET keeps a separate before-cleaner curve.
            if directory == "lavik-baseline1m-20260926" and row["operation"] == "GET":
                row["product"] = "Lavik"
            key = (row["size_bytes"], row["operation"], row["connections"],
                   row["product"])
            rows[key] = row
    output = ROOT / "results.csv"
    with output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        for row in sorted(rows.values(), key=lambda item: (
                item["size_bytes"], item["operation"], item["connections"],
                item["product"])):
            writer.writerow(row)
    print(f"{len(rows)} rows: {output}")


if __name__ == "__main__":
    main()
