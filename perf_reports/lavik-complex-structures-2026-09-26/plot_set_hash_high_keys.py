#!/usr/bin/env python3
"""Replace one Hash/Set chart only after all four products finish the same run."""

import argparse
import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parent
POINT_LEVELS = (80, 320, 1280, 2560, 5120)
FULL_LEVELS = {1048576: (16, 80), 104857600: (1, 4, 16)}
SIZES = {1048576: ("1m", 50000, "1 MiB"),
         104857600: ("100m", 500, "100 MiB")}
COMMANDS = {"hash": ("HGET", "HSET", "HGETALL"),
            "set": ("SISMEMBER", "SADD_SREM", "SMEMBERS")}
PRODUCTS = ("redis", "valkey", "kvrocks", "lavik")
MAIN_COMMIT = "d1ce200e174adcb07820b5431c77b024350e85b6"
MAIN_BINARY_SHA256 = "bd3f942e3b7b0f46c23c716197c8cc4ec8ad963e92cede0d9fa2574ff52a74a9"
LABELS = {"redis": "Redis", "valkey": "Valkey", "kvrocks": "Kvrocks",
          "lavik": "Lavik main"}
STYLES = {"redis": ("#bd3f43", "o", "-"),
          "valkey": ("#008681", "s", "-"),
          "kvrocks": ("#a75b19", "D", "-"),
          "lavik": ("#6574bc", "^", "--"),
          "variant": ("#7b4d9f", "v", ":")}


def load(product, kind, size, field, variant=None):
    size_tag, keys, _ = SIZES[size]
    tag = f"{kind}-{size_tag}-k{keys}-f{field}-20260929"
    if product == "variant":
        tag = variant["tag"]
    elif product == "lavik":
        tag = f"main{MAIN_COMMIT[:8]}-" + tag
    prefix = "lavik" if product == "variant" else product
    folder = ROOT / "raw" / f"{prefix}-{tag}"
    if not (folder / "complete.json").exists():
        raise RuntimeError(f"run is incomplete: {folder}")
    provenance = list(folder.glob("provenance-*.json"))
    if len(provenance) != 1:
        raise RuntimeError(f"expected one provenance file: {folder}")
    options = json.loads(provenance[0].read_text())
    expected_options = {"keys": keys, "sizes": [size], "fields": [field],
                        "types": [kind], "levels": list(POINT_LEVELS),
                        "full_levels": list(FULL_LEVELS[size]), "seconds": 8,
                        "mode": "both"}
    for name, expected in expected_options.items():
        if options.get(name) != expected:
            raise RuntimeError(f"{folder}: {name}={options.get(name)}, expected {expected}")
    if product == "lavik" and options.get("source_commit") != MAIN_COMMIT:
        raise RuntimeError(f"{folder}: not the measured main {MAIN_COMMIT}")
    if product == "lavik" and options.get("sha256") != MAIN_BINARY_SHA256:
        raise RuntimeError(f"{folder}: unexpected Lavik binary SHA256")
    if product == "variant":
        if options.get("source_commit") != variant["commit"]:
            raise RuntimeError(f"{folder}: unexpected variant source commit")
        if options.get("sha256") != variant["sha256"]:
            raise RuntimeError(f"{folder}: unexpected variant binary SHA256")
    if not (folder / f"{kind}-{size}-{field}.validated.json").exists():
        raise RuntimeError(f"seed was not validated: {folder}")
    results = {}
    failures = {}
    for path in folder.glob("*.result.json"):
        row = json.loads(path.read_text())
        if any(row.get(name) != value for name, value in
               (("product", folder.name), ("type", kind), ("logical_bytes", size),
                ("field_bytes", field), ("keys", keys))):
            raise RuntimeError(f"mismatched result: {path}")
        point = (row["operation"], row["connections"])
        if point in results:
            raise RuntimeError(f"duplicate result: {path}")
        results[point] = row
    for path in folder.glob("*.error.json"):
        row = json.loads(path.read_text())
        point = (row["operation"], row["connections"])
        if point in failures or point in results:
            raise RuntimeError(f"duplicate or conflicting result: {path}")
        failures[point] = row["error"]
    commands = COMMANDS[kind]
    expected = {(command, connections)
                for command in commands
                for connections in (FULL_LEVELS[size] if command == commands[2]
                                    else POINT_LEVELS)}
    if set(results) | set(failures) != expected:
        raise RuntimeError(f"{folder}: incomplete grid: {expected - set(results) - set(failures)}")
    return results, failures, folder


def draw(kind, size, field, full, datasets, products, labels):
    commands = COMMANDS[kind][2:] if full else COMMANDS[kind][:2]
    fig, axes = plt.subplots(1, len(commands),
                             figsize=(6.8 if full else 12.8, 4.6), squeeze=False)
    for ax, command in zip(axes[0], commands):
        for product in products:
            results, failures, _ = datasets[product]
            points = [(level, float(results[(command, level)]["qps"]))
                      for level in (FULL_LEVELS[size] if full else POINT_LEVELS)
                      if (command, level) in results]
            if points:
                color, marker, line = STYLES[product]
                scale = 1 if full else 1000
                # Equal throughput can put products directly on top of one
                # another (notably 1 MiB SMEMBERS). An open Redis marker on
                # top keeps those measurements visible at their exact x value.
                ax.plot([level for level, _ in points],
                        [qps / scale for _, qps in points],
                        color=color, marker=marker, linestyle=line, linewidth=2,
                        markersize=9 if product == "redis" else 6,
                        markerfacecolor="none" if product == "redis" else color,
                        markeredgewidth=1.8 if product == "redis" else 1,
                        zorder=5 if product == "redis" else 3,
                        label=("Kvrocks (80 GiB cache)" if product == "kvrocks"
                               else labels[product]))
            failed = [level for (op, level) in failures if op == command]
            if failed:
                ax.text(0.98, 0.04 + 0.06 * products.index(product),
                        f"{labels[product]} failed: {','.join(map(str, sorted(failed)))}",
                        transform=ax.transAxes, ha="right", fontsize=8)
        ax.set_title(command.replace("_", " + "))
        ax.set_xlabel("Connections (log scale)")
        ax.set_xscale("log")
        ax.grid(alpha=0.22)
        ax.set_ylabel("Throughput (QPS)" if full else "Throughput (k QPS)")
        if not full and command == COMMANDS[kind][1]:
            ax.set_yscale("log")
            ax.set_ylabel("Throughput (k QPS, log scale)")
        ax.legend(fontsize=8)
    _, keys, size_label = SIZES[size]
    fig.suptitle(f"{kind.capitalize()} · {size_label}/key · {keys:,} keys · {field} B/entry")
    fig.tight_layout()
    suffix = "-full" if full else ""
    destination = ROOT / "charts" / f"{kind}-{size}-{field}-ab{suffix}.png"
    fig.savefig(destination, dpi=150)
    plt.close(fig)
    print(destination)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=COMMANDS)
    parser.add_argument("size", type=int, choices=SIZES)
    parser.add_argument("field", type=int, choices=(128, 1024))
    parser.add_argument("--variant-tag", help="Completed Lavik run tag")
    parser.add_argument("--variant-label", help="Legend label, such as Lavik PR #123")
    parser.add_argument("--variant-commit", help="Exact variant source commit")
    parser.add_argument("--variant-sha256", help="Exact variant binary SHA256")
    args = parser.parse_args()
    variant_options = (args.variant_tag, args.variant_label,
                       args.variant_commit, args.variant_sha256)
    if any(variant_options) and not all(variant_options):
        parser.error("all four --variant-* options are required together")
    variant = ({"tag": args.variant_tag, "commit": args.variant_commit,
                "sha256": args.variant_sha256} if args.variant_tag else None)
    products = (*PRODUCTS, "variant") if variant else PRODUCTS
    labels = dict(LABELS)
    if variant:
        labels["variant"] = args.variant_label
    datasets = {product: load(product, args.kind, args.size, args.field, variant)
                for product in products}
    draw(args.kind, args.size, args.field, False, datasets, products, labels)
    draw(args.kind, args.size, args.field, True, datasets, products, labels)
    destination = ROOT / f"{args.kind}-{args.size}-{args.field}-high-keys.csv"
    with destination.open("w", newline="") as output:
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(("product", "type", "logical_bytes", "field_bytes",
                         "keys", "operation", "connections", "qps", "error"))
        for product in products:
            results, failures, folder = datasets[product]
            product_name = folder.name if product == "variant" else product
            for (command, connections), row in sorted(results.items()):
                writer.writerow((product_name, args.kind, args.size, args.field,
                                 SIZES[args.size][1], command, connections,
                                 row["qps"], ""))
            for (command, connections), error in sorted(failures.items()):
                writer.writerow((product_name, args.kind, args.size, args.field,
                                 SIZES[args.size][1], command, connections,
                                 "", error.splitlines()[0]))
    print(destination)


if __name__ == "__main__":
    main()
