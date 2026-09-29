#!/usr/bin/env python3
"""Plot validated Lavik RESTORE times from identical empty-disk seed runs."""

import argparse
import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parent
COLORS = ("#6574bc", "#b25f84", "#7b4d9f", "#556b2f")


def read_json(path):
    return json.loads(path.read_text())


def load_run(condition, run):
    folder = ROOT / "raw" / f"lavik-{run['tag']}"
    complete = read_json(folder / "complete.json")
    if complete["failures_total"] or read_json(folder / "server-exit.json")["code"]:
        raise RuntimeError(f"incomplete or failed run: {folder}")
    provenance = list(folder.glob("provenance-*.json"))
    if len(provenance) != 1:
        raise RuntimeError(f"expected one provenance file: {folder}")
    options = read_json(provenance[0])
    expected = {
        "source_commit": run["commit"], "sha256": run["sha256"],
        "types": [condition["kind"]], "sizes": [condition["logical_bytes"]],
        "fields": [condition["field_bytes"]], "keys": condition["keys"],
        "fill_workers": 8,
    }
    for name, value in expected.items():
        if options.get(name) != value:
            raise RuntimeError(f"{folder}: unexpected {name}={options.get(name)}")
    seed_sha = options.get("seed_dump_sha256")
    if not seed_sha:
        raise RuntimeError(f"{folder}: missing RDB seed hash")
    stem = f"{condition['kind']}-{condition['logical_bytes']}-{condition['field_bytes']}"
    fill = read_json(folder / f"{stem}.fill.json")
    if fill.get("method") != "restore" or fill.get("commands") != condition["keys"]:
        raise RuntimeError(f"{folder}: unexpected fill method or command count")
    validated = read_json(folder / f"{stem}.validated.json")
    entries = condition["logical_bytes"] // condition["field_bytes"]
    cardinalities = validated["sample_cardinalities"]
    if (validated["keys"] != condition["keys"] or
            validated["entries_per_key"] != entries or
            len(cardinalities) != condition["keys"] or
            any(count != entries for count in cardinalities.values())):
        raise RuntimeError(f"{folder}: incomplete key validation")
    return float(fill["seconds"]), seed_sha


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("condition", help="Entry in restore_import_runs.json")
    args = parser.parse_args()
    conditions = read_json(ROOT / "restore_import_runs.json")
    condition = conditions[args.condition]
    runs = condition["runs"]
    if len(runs) < 2:
        raise RuntimeError("RESTORE comparison needs at least two runs")
    measured = [load_run(condition, run) for run in runs]
    if len({seed_sha for _, seed_sha in measured}) != 1:
        raise RuntimeError("RESTORE runs used different RDB seed payloads")

    seconds = [value for value, _ in measured]
    baseline = seconds[0]
    fig, ax = plt.subplots(figsize=(9.2, 4.8))
    bars = ax.barh([run["label"] for run in runs], seconds,
                   color=[COLORS[index % len(COLORS)]
                          for index in range(len(runs))], height=0.58)
    ax.invert_yaxis()
    ax.set_xlim(0, max(seconds) * 1.24)
    ax.set_xlabel("RESTORE fill time (seconds; lower is better)")
    ax.set_title(f"{condition['kind'].capitalize()} · "
                 f"{condition['logical_bytes'] // 1048576} MiB/key · "
                 f"{condition['keys']} keys · {condition['field_bytes']} B/entry")
    ax.grid(axis="x", alpha=0.22)
    ax.set_axisbelow(True)
    for index, (bar, value) in enumerate(zip(bars, seconds)):
        speedup = "baseline" if index == 0 else f"{baseline / value:.1f}× faster"
        ax.text(value + max(seconds) * 0.018, bar.get_y() + bar.get_height() / 2,
                f"{value:,.1f} s  ·  {speedup}", va="center", fontsize=10)
    fig.text(0.5, 0.01,
             "Same validated RDB payload · eight RESTORE clients · empty six-NVMe SPDK dataset",
             ha="center", fontsize=9, color="#555555")
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    chart = ROOT / "charts" / f"{args.condition}-restore-ab.png"
    fig.savefig(chart, dpi=150)
    plt.close(fig)
    print(chart)

    csv_path = ROOT / f"{args.condition}-restore-ab.csv"
    with csv_path.open("w", newline="") as output:
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(("label", "source_commit", "binary_sha256", "seconds",
                         "speedup_vs_main", "seed_dump_sha256", "keys"))
        for run, (value, seed_sha) in zip(runs, measured):
            writer.writerow((run["label"], run["commit"], run["sha256"],
                             value, baseline / value, seed_sha,
                             condition["keys"]))
    print(csv_path)


if __name__ == "__main__":
    main()
