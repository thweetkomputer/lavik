#!/usr/bin/env python3
"""Plot Set/Hash main and every measured PR with the existing peer results."""

import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
SIZES = (1048576, 10485760, 104857600)
FIELDS = (128, 1024)
PEER_10M_TAG = "10m-k64-20260929"
COMMANDS = {
    "hash": ("HGET", "HSET", "HGETALL"),
    "set": ("SISMEMBER", "SADD_SREM", "SMEMBERS"),
}
STYLES = {
    "Redis": ("#bd3f43", "o", "-"),
    "Valkey": ("#008681", "s", "-"),
    "Kvrocks": ("#a75b19", "D", "-"),
}


def identity(row):
    return (row["type"], int(row["logical_bytes"]),
            int(row["field_bytes"]), row["operation"],
            int(row["connections"]))


def load_run(product, tag):
    folder = ROOT / "raw" / f"{product}-{tag}"
    if not (folder / "complete.json").exists():
        raise RuntimeError(f"incomplete run: {folder}")
    results = {}
    for path in folder.glob("*.result.json"):
        row = json.loads(path.read_text())
        key = identity(row)
        if key in results:
            raise RuntimeError(f"duplicate result: {key}")
        results[key] = row
    failures = {}
    for path in folder.glob("*.error.json"):
        row = json.loads(path.read_text())
        failures[identity(row)] = row["error"]
    if set(results) & set(failures):
        raise RuntimeError(f"both result and error in {folder}")
    return results, failures


def expected_grid(size):
    point_levels = (80, 320, 1280, 2560, 5120)
    full_levels = {1048576: (16, 80), 10485760: (4, 16),
                   104857600: (1, 4, 16)}[size]
    return {(kind, size, field, command, connections)
            for kind, commands in COMMANDS.items()
            for field in FIELDS
            for command in commands
            for connections in (full_levels if command == commands[2]
                                else point_levels)}


def main():
    # A new variant can be published one completed key size at a time. Earlier
    # variants remain plotted while its other sizes are still running.
    variants = json.loads((ROOT / "set-hash-variants.json").read_text())[
        "lavik_variants"]
    labels = [variant["label"] for variant in variants]
    if len(labels) != len(set(labels)) or not labels or labels[0] != "Lavik main":
        raise RuntimeError("variants require unique labels and Lavik main first")
    styles = {**STYLES, "Lavik main": ("#6574bc", "^", "--")}
    prs = variants[1:]
    for index, variant in enumerate(prs):
        fraction = index / max(1, len(prs) - 1)
        styles[variant["label"]] = (
            plt.get_cmap("turbo")(0.08 + 0.82 * fraction), "^", "-")

    with (ROOT / "results.csv").open(newline="") as source:
        historical = list(csv.DictReader(source))
    peer_rows = {name: {} for name in ("Redis", "Valkey", "Kvrocks")}
    for row in historical:
        name = row["product"].capitalize()
        if name in peer_rows and row["type"] in COMMANDS:
            key = identity(row)
            if key in peer_rows[name]:
                raise RuntimeError(f"duplicate peer result: {name} {key}")
            peer_rows[name][key] = row
    for name in peer_rows:
        rows, errors = load_run(name.lower(), PEER_10M_TAG)
        expected = expected_grid(10485760)
        if set(rows) | set(errors) != expected:
            raise RuntimeError(f"wrong {name} 10 MiB grid: "
                               f"missing={expected - set(rows) - set(errors)}, "
                               f"extra={(set(rows) | set(errors)) - expected}")
        if errors:
            raise RuntimeError(f"{name} 10 MiB failures: {errors}")
        peer_rows[name].update(rows)
    for name, rows in peer_rows.items():
        for size in SIZES:
            missing = expected_grid(size) - set(rows)
            if missing:
                raise RuntimeError(f"missing {name} peers: {len(missing)}")
    runs = {}
    failures = {}
    for size in SIZES:
        for variant in variants:
            name = variant["label"]
            tag = variant["runs"].get(str(size))
            if tag is None:
                continue
            rows, errors = load_run("lavik", tag)
            expected = expected_grid(size)
            if set(rows) | set(errors) != expected:
                raise RuntimeError(f"wrong {tag} grid: "
                                   f"missing={expected - set(rows) - set(errors)}, "
                                   f"extra={(set(rows) | set(errors)) - expected}")
            runs[(name, size)] = rows
            failures[(name, size)] = errors

    chart_dir = ROOT / "charts"
    chart_dir.mkdir(exist_ok=True)
    summary = []
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False,
                         "axes.spines.right": False, "figure.facecolor": "white"})
    for kind, commands in COMMANDS.items():
        for size in SIZES:
            for field in FIELDS:
                for full in (False, True):
                    selected = commands[2:] if full else commands[:2]
                    fig, axes = plt.subplots(1, len(selected),
                                             figsize=(6.8 if full else 12.8, 4.6),
                                             squeeze=False)
                    plotted = 0
                    for ax, command in zip(axes[0], selected):
                        for name in styles:
                            if name not in peer_rows and (name, size) not in runs:
                                continue
                            rows = peer_rows[name] if name in peer_rows else runs[(name, size)]
                            points = sorted(
                                ((key[-1], float(row["qps"]))
                                 for key, row in rows.items()
                                 if key[:4] == (kind, size, field, command)),
                                key=lambda point: point[0])
                            if not points:
                                continue
                            plotted += 1
                            color, marker, line = styles[name]
                            label = ("Kvrocks (80 GiB cache)"
                                     if name == "Kvrocks" else name)
                            scale = 1 if full else 1000
                            ax.plot([x for x, _ in points], [y / scale for _, y in points],
                                    color=color, marker=marker, linestyle=line,
                                    linewidth=2, label=label)
                            for connections, qps in points:
                                summary.append((name, kind, size, field, command,
                                                connections, qps))
                        ax.set_title(command.replace("_", " + "))
                        ax.set_xlabel("Connections (log scale)")
                        ax.set_xscale("log")
                        ax.grid(alpha=0.22)
                        ax.set_ylabel("Throughput (QPS)" if full
                                      else "Throughput (k QPS)")
                        if not full and command == commands[1]:
                            # Durable writes differ by two orders of magnitude;
                            # a linear axis hides both Lavik curves at zero.
                            ax.set_yscale("log")
                            ax.set_ylabel("Throughput (k QPS, log scale)")
                        oom_variants = sum(
                            any(key[:4] == (kind, size, field, command) and
                                "OOM grouped operation scratch admission" in reason
                                for key, reason in failures[(name, size)].items())
                            for name in labels if (name, size) in failures)
                        if oom_variants:
                            ax.text(0.98, 0.04,
                                    f"{oom_variants} Lavik variants: OOM",
                                    transform=ax.transAxes, ha="right", fontsize=8)
                        ax.legend(fontsize=8)
                    if not plotted:
                        raise RuntimeError((kind, size, field, full))
                    size_label = {1048576: "1 MiB", 10485760: "10 MiB",
                                  104857600: "100 MiB"}[size]
                    fig.suptitle(f"{kind.capitalize()} · {size_label}/key · {field} B/entry")
                    fig.tight_layout()
                    suffix = "-full" if full else ""
                    fig.savefig(chart_dir / f"{kind}-{size}-{field}-ab{suffix}.png",
                                dpi=150)
                    plt.close(fig)
    with (ROOT / "set-hash-ab.csv").open("w", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(("product", "type", "logical_bytes", "field_bytes",
                         "operation", "connections", "qps"))
        writer.writerows(summary)
    for (name, size), errors in failures.items():
        for key, message in errors.items():
            reason = ("OOM grouped operation scratch admission"
                      if "OOM grouped operation scratch admission" in message
                      else message.splitlines()[0][:120])
            print(f"{name} {size} {key}: {reason}")


if __name__ == "__main__":
    main()
