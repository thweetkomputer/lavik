#!/usr/bin/env python3
"""Plot validated 500-key import times with each product's fill method shown."""

import argparse
import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parent
SIZE = 104857600
FIELD = 128
KEYS = 500
ENTRY_COUNT = SIZE // FIELD
PR_COMMIT = "c96d9d0baf01be5ced503f7c3f2d90be4987477a"
PR_SHA256 = "1dc0f82abba4d708342cace5dfff07ff8d2c59768e39b07631e326641a95adb7"
PRODUCTS = (
    ("redis", "Redis", "#bd3f43"),
    ("valkey", "Valkey", "#008681"),
    ("kvrocks", "Kvrocks", "#a75b19"),
    ("lavik", "Lavik PR #219", "#7b4d9f"),
)


def read_json(path):
    return json.loads(path.read_text())


def read_run(kind, product):
    prefix = ("import128m-c96d9d0b-" if product == "lavik" else "")
    tag = f"{prefix}{kind}-100m-k500-f128-20260929"
    folder = ROOT / "raw" / f"{product}-{tag}"
    complete = read_json(folder / "complete.json")
    if complete["failures_total"] or read_json(folder / "server-exit.json")["code"]:
        raise RuntimeError(f"failed run: {folder}")
    provenance = list(folder.glob("provenance-*.json"))
    if len(provenance) != 1:
        raise RuntimeError(f"expected one provenance file: {folder}")
    options = read_json(provenance[0])
    expected = {"keys": KEYS, "types": [kind], "sizes": [SIZE],
                "fields": [FIELD]}
    if product == "lavik":
        expected["fill_workers"] = 8
    for name, value in expected.items():
        if options.get(name) != value:
            raise RuntimeError(f"{folder}: unexpected {name}")
    if product == "lavik" and (options.get("source_commit") != PR_COMMIT or
                               options.get("sha256") != PR_SHA256):
        raise RuntimeError(f"unexpected Lavik PR build: {folder}")
    stem = f"{kind}-{SIZE}-{FIELD}"
    filled = read_json(folder / f"{stem}.fill.json")
    command = "SADD" if kind == "set" else "HSET"
    method = "RESTORE" if product == "lavik" else f"batched {command}"
    expected_commands = KEYS if product == "lavik" else KEYS * ENTRY_COUNT // 128
    if filled.get("commands") != expected_commands:
        raise RuntimeError(f"unexpected fill count: {folder}")
    if product == "lavik" and filled.get("method") != "restore":
        raise RuntimeError(f"unexpected RESTORE fill: {folder}")
    if product != "lavik" and filled.get("entries_per_command") != 128:
        raise RuntimeError(f"unexpected peer fill batch: {folder}")
    validated = read_json(folder / f"{stem}.validated.json")
    cardinalities = validated["sample_cardinalities"]
    if (validated["keys"] != KEYS or validated["entries_per_key"] != ENTRY_COUNT or
            len(cardinalities) != KEYS or
            any(value != ENTRY_COUNT for value in cardinalities.values())):
        raise RuntimeError(f"incomplete validation: {folder}")
    return {"product": product, "method": method,
            "seconds": float(filled["seconds"]), "folder": folder.name}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=("hash", "set"))
    args = parser.parse_args()
    rows = [read_run(args.kind, product) for product, _, _ in PRODUCTS]

    fig, ax = plt.subplots(figsize=(9.2, 4.8))
    labels = [f"{label} · {row['method']}" for row, (_, label, _) in
              zip(rows, PRODUCTS)]
    seconds = [row["seconds"] for row in rows]
    colors = [color for _, _, color in PRODUCTS]
    bars = ax.barh(labels, seconds, color=colors, height=0.58)
    ax.invert_yaxis()
    ax.set_xlim(0, max(seconds) * 1.24)
    ax.set_xlabel("Fill time (seconds; lower is better)")
    ax.set_title(f"{args.kind.capitalize()} · 100 MiB/key · 500 keys · 128 B/entry")
    ax.grid(axis="x", alpha=0.22)
    ax.set_axisbelow(True)
    for bar, value in zip(bars, seconds):
        ax.text(value + max(seconds) * 0.018,
                bar.get_y() + bar.get_height() / 2,
                f"{value:,.1f} s", va="center", fontsize=10)
    fig.text(0.5, 0.01,
             "All 500 keys validated · persistence settings differ between products",
             ha="center", fontsize=9, color="#555555")
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    destination = ROOT / "charts" / f"{args.kind}-104857600-128-k500-fill.png"
    fig.savefig(destination, dpi=150)
    plt.close(fig)
    print(destination)

    csv_path = ROOT / f"{args.kind}-104857600-128-k500-fill.csv"
    with csv_path.open("w", newline="") as output:
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(("product", "method", "seconds", "raw_run"))
        for row in rows:
            writer.writerow((row["product"], row["method"], row["seconds"],
                             row["folder"]))
    print(csv_path)


if __name__ == "__main__":
    main()
