#!/usr/bin/env python3
"""Compare validated Hash/Set fills using the same batched write commands."""

import argparse
import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parent
PRODUCTS = (
    ("redis", "Redis", "#bd3f43"),
    ("valkey", "Valkey", "#008681"),
    ("kvrocks", "Kvrocks", "#a75b19"),
    ("lavik", "Lavik main", "#6574bc"),
)


def read_json(path):
    return json.loads(path.read_text())


def read_run(kind, product, lavik_run, size, field, fill):
    keys = 50000 if size == 1048576 else 500
    entries = size // field
    step = min(1024, max(16, fill["batch_bytes"] // field))
    size_tag = "1m" if size == 1048576 else "100m"
    tag = (lavik_run["tag"] if product == "lavik" else
           fill["peer_tag"] or f"{kind}-{size_tag}-k{keys}-f{field}-20260929")
    folder = ROOT / "raw" / f"{product}-{tag}"
    complete = read_json(folder / "complete.json")
    if complete["failures_total"] or read_json(folder / "server-exit.json")["code"]:
        raise RuntimeError(f"failed run: {folder}")
    provenance = list(folder.glob("provenance-*.json"))
    if len(provenance) != 1:
        raise RuntimeError(f"expected one provenance file: {folder}")
    options = read_json(provenance[0])
    expected = {"keys": keys, "types": [kind], "sizes": [size],
                "fields": [field], "seed_pipeline": fill["pipeline"]}
    if product == "lavik" or fill["peer_tag"]:
        expected["fill_workers"] = fill["workers"]
        expected["seed_command_bytes"] = fill["batch_bytes"]
    for name, value in expected.items():
        if options.get(name) != value:
            raise RuntimeError(f"{folder}: unexpected {name}")
    if product == "lavik" and (
            options.get("source_commit") != lavik_run["commit"] or
            options.get("sha256") != lavik_run["sha256"]):
        raise RuntimeError(f"unexpected Lavik build: {folder}")
    stem = f"{kind}-{size}-{field}"
    filled = read_json(folder / f"{stem}.fill.json")
    command = "SADD" if kind == "set" else "HSET"
    method = f"batched {command}"
    expected_commands = keys * entries // step
    if filled.get("commands") != expected_commands:
        raise RuntimeError(f"unexpected fill count: {folder}")
    if filled.get("method") == "restore":
        raise RuntimeError(f"RESTORE cannot be compared with batched {command}: {folder}")
    if filled.get("entries_per_command", step) != step:
        raise RuntimeError(f"unexpected fill batch: {folder}")
    validated = read_json(folder / f"{stem}.validated.json")
    cardinalities = validated["sample_cardinalities"]
    if (validated["keys"] != keys or validated["entries_per_key"] != entries or
            len(cardinalities) != keys or
            any(value != entries for value in cardinalities.values())):
        raise RuntimeError(f"incomplete validation: {folder}")
    return {"product": product, "method": method,
            "seconds": float(filled["seconds"]), "folder": folder.name}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=("hash", "set"))
    parser.add_argument("--size", type=int, choices=(1048576, 104857600), default=104857600)
    parser.add_argument("--field", type=int, choices=(128, 1024), default=128)
    parser.add_argument("--lavik-tag", required=True, help="Completed Lavik run tag")
    parser.add_argument("--lavik-commit", required=True)
    parser.add_argument("--lavik-sha256", required=True)
    parser.add_argument("--peer-tag", help="Common fresh run tag for Redis, Valkey and Kvrocks")
    parser.add_argument("--fill-workers", type=int, default=8)
    parser.add_argument("--pipeline", type=int, default=64)
    parser.add_argument("--batch-bytes", type=int, default=16384)
    parser.add_argument("--lavik-label", default="Lavik main")
    parser.add_argument("--pr-tag", help="Completed fresh PR fill; never a reused seed")
    parser.add_argument("--pr-commit")
    parser.add_argument("--pr-sha256")
    parser.add_argument("--pr-label", default="Lavik PR #222")
    args = parser.parse_args()
    if any((args.pr_tag, args.pr_commit, args.pr_sha256)) and not all(
            (args.pr_tag, args.pr_commit, args.pr_sha256)):
        parser.error("--pr-tag, --pr-commit and --pr-sha256 are required together")
    lavik_run = {
        "tag": args.lavik_tag,
        "commit": args.lavik_commit, "sha256": args.lavik_sha256,
    }
    fill = {"peer_tag": args.peer_tag, "workers": args.fill_workers,
            "pipeline": args.pipeline, "batch_bytes": args.batch_bytes}
    rows = [read_run(args.kind, product, lavik_run, args.size, args.field, fill)
            for product, _, _ in PRODUCTS]

    products = list(PRODUCTS)
    if args.pr_tag:
        pr = read_run(args.kind, "lavik", {
            "tag": args.pr_tag, "commit": args.pr_commit,
            "sha256": args.pr_sha256}, args.size, args.field, fill)
        pr["product"] = "lavik-pr"
        rows.append(pr)
        products.append(("lavik-pr", args.pr_label, "#7b4d9f"))
    keys = 50000 if args.size == 1048576 else 500
    size_mib = args.size // 1048576
    fig, ax = plt.subplots(figsize=(9.2, 4.8))
    labels = [f"{args.lavik_label if product == 'lavik' else label} · {row['method']}"
              for row, (product, label, _) in zip(rows, products)]
    seconds = [row["seconds"] for row in rows]
    colors = [color for _, _, color in products]
    bars = ax.barh(labels, seconds, color=colors, height=0.58)
    ax.invert_yaxis()
    ax.set_xlim(0, max(seconds) * 1.24)
    ax.set_xlabel("Fill time (seconds; lower is better)")
    ax.set_title(f"{args.kind.capitalize()} · {size_mib} MiB/key · {keys:,} keys · {args.field} B/entry")
    ax.grid(axis="x", alpha=0.22)
    ax.set_axisbelow(True)
    for bar, value in zip(bars, seconds):
        ax.text(value + max(seconds) * 0.018,
                bar.get_y() + bar.get_height() / 2,
                f"{value:,.1f} s", va="center", fontsize=10)
    fig.text(0.5, 0.01,
             f"{args.fill_workers} clients · {min(1024, max(16, args.batch_bytes // args.field))} entries/command · pipeline {args.pipeline} · persistence settings differ",
             ha="center", fontsize=9, color="#555555")
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    destination = ROOT / "charts" / f"{args.kind}-{args.size}-{args.field}-k{keys}-fill.png"
    fig.savefig(destination, dpi=150)
    plt.close(fig)
    print(destination)

    csv_path = ROOT / f"{args.kind}-{args.size}-{args.field}-k{keys}-fill.csv"
    with csv_path.open("w", newline="") as output:
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(("product", "method", "seconds", "raw_run"))
        for row in rows:
            writer.writerow((row["product"], row["method"], row["seconds"],
                             row["folder"]))
    print(csv_path)


if __name__ == "__main__":
    main()
