#!/usr/bin/env python3
"""Draw ordered-collection main/PR curves from explicit measured revisions.

Peer runs retain their original workload and raw result provenance. No older
Lavik result is relabeled as a freshly measured source revision.
"""
import argparse
import csv
import json
from pathlib import Path

import plot_set_hash_high_keys as chart

ROOT = Path(__file__).resolve().parent
COMMANDS = {"list": ("LINDEX", "LSET", "LRANGE"),
            "zset": ("ZSCORE", "ZINCRBY", "ZRANGE"),
            "stream": ("XRANGE", "XADD_MAXLEN", "XRANGE_FULL")}


def load(folder, condition, revision=None):
    kind, size, field, keys = condition
    complete = json.loads((folder / "complete.json").read_text())
    if revision is not None:
        provenance = list(folder.glob("provenance-*.json"))
        if len(provenance) != 1:
            raise ValueError(f"ambiguous provenance: {folder}")
        source = json.loads(provenance[0].read_text())
        expected = {"source_commit": revision["commit"],
                    "sha256": revision["sha256"], "keys": keys,
                    "types": [kind], "sizes": [size], "fields": [field],
                    "seconds": 8, "mode": "both",
                    "levels": list(chart.POINT_LEVELS),
                    "full_levels": list(chart.FULL_LEVELS[size])}
        for name, value in expected.items():
            if source.get(name) != value:
                raise ValueError(f"{folder}: mismatched {name}")
        if json.loads((folder / "server-exit.json").read_text())["code"] != 0:
            raise ValueError(f"unclean server exit: {folder}")
        for stage in ("validated", "after"):
            counts = json.loads((folder / f"{kind}-{size}-{field}.{stage}.json")
                                .read_text())["sample_cardinalities"]
            if len(counts) != keys:
                raise ValueError(f"incomplete cardinality checks: {folder}")
            # A reused Stream retains the previous XADD MAXLEN ~ result;
            # approximate trimming can keep one extra macro-node at startup.
            post_write = stage == "after" or source.get("reused_seed_from")
            delta = 100 if kind == "stream" and post_write else 0
            if any(abs(count - size // field) > delta for count in counts.values()):
                raise ValueError(f"changed cardinality: {folder}")
        if complete["failures_total"] != len(list(folder.glob("*.error.json"))):
            raise ValueError(f"failure inventory differs: {folder}")
    results, failures = {}, {}
    for suffix, target in (("result", results), ("error", failures)):
        for path in folder.glob(f"{kind}-{size}-{field}-*.{suffix}.json"):
            row = json.loads(path.read_text())
            point = (row["operation"], row["connections"])
            if point in results or point in failures:
                raise ValueError(f"duplicate/conflicting point: {path}")
            if suffix == "result":
                for name, value in (("type", kind), ("logical_bytes", size),
                                    ("field_bytes", field), ("keys", keys),
                                    ("seconds", 8)):
                    if row.get(name) != value:
                        raise ValueError(f"{path}: mismatched {name}")
                target[point] = row
            else:
                target[point] = row["error"]
    expected = {(command, level) for command in COMMANDS[kind]
                for level in (chart.FULL_LEVELS[size]
                              if command == COMMANDS[kind][-1]
                              else chart.POINT_LEVELS)}
    if results.keys() | failures.keys() != expected:
        raise ValueError(f"incomplete grid: {folder}")
    return results, failures, folder


def draw_stream(size, field, keys, datasets, labels):
    for command in COMMANDS["stream"]:
        full = command == "XRANGE_FULL"
        levels = chart.FULL_LEVELS[size] if full else chart.POINT_LEVELS
        fig, ax = chart.plt.subplots(figsize=(8.6, 4.8))
        for product, (rows, failures, _) in datasets.items():
            color, marker, line = chart.STYLES[product]
            values = [rows[(command, n)]["qps"] / (1 if full else 1000)
                      if (command, n) in rows else float("nan") for n in levels]
            ax.plot(levels, values, color=color, marker=marker, linestyle=line,
                    linewidth=2, label=("Kvrocks (80 GiB cache)"
                                        if product == "kvrocks" else labels[product]))
            failed = [n for n in levels if (command, n) in failures]
            if failed:
                ax.text(.98, .04 + .06 * list(datasets).index(product),
                        f"{labels[product]} failed: {failed}",
                        ha="right", transform=ax.transAxes, fontsize=8)
        ax.set_xscale("log")
        ax.set_xlabel("Connections (log scale)")
        ax.set_ylabel("Throughput (QPS)" if full else "Throughput (k QPS)")
        if command == "XADD_MAXLEN":
            ax.set_yscale("log")
            ax.set_ylabel("Throughput (k QPS, log scale)")
        else:
            ax.set_ylim(bottom=0)
        ax.grid(alpha=.22)
        ax.legend(fontsize=8)
        ax.set_title(f"Stream · {size / 1048576:g} MiB/key · {keys} keys · "
                     f"{field} B/entry\n{command.replace('_', ' ')}")
        fig.tight_layout()
        destination = ROOT / "charts" / f"stream-{size}-{field}-{command.lower()}-latest.png"
        fig.savefig(destination, dpi=150, bbox_inches="tight")
        chart.plt.close(fig)
        print(destination)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    # Preserve each PR's color across workloads, including charts where an
    # earlier variant has no measurements. Array position alone is unstable.
    variant_styles = (chart.STYLES["variant0"], *chart.EXTRA_VARIANT_STYLES)
    for condition in manifest["plots"]:
        kind, size, field, keys = (condition[name]
                                   for name in ("kind", "size", "field", "keys"))
        if kind not in COMMANDS or keys != (8 if size == 104857600 else 64):
            raise ValueError("ordered workload must match the existing peers")
        chart.COMMANDS[kind] = COMMANDS[kind]
        chart.SIZES[size] = (str(size), keys, f"{size / 1048576:g} MiB")
        chart.FULL_LEVELS[size] = (1, 4, 16) if size == 104857600 else (16, 80)
        datasets, labels = {}, dict(chart.LABELS)
        for product in ("redis", "valkey", "kvrocks"):
            suffix = "-100m" if size == 104857600 else ""
            datasets[product] = load(ROOT / "raw" / (product + suffix),
                                     (kind, size, field, keys))
        versions = [("lavik", condition["main"])]
        versions.extend((f"variant{i}", revision) for i, revision in
                        enumerate(condition.get("variants", [])))
        for i, (product, revision) in enumerate(versions):
            labels[product] = revision["label"] + " " + revision["commit"][:8]
            if i > 0:
                style = revision.get("style_index", i - 1)
                if not isinstance(style, int) or not 0 <= style < len(variant_styles):
                    raise ValueError("invalid variant style index")
                chart.STYLES[product] = variant_styles[style]
            datasets[product] = load(ROOT / "raw" / ("lavik-" + revision["tag"]),
                                     (kind, size, field, keys), revision)
        products = tuple(datasets)
        if kind == "stream":
            draw_stream(size, field, keys, datasets, labels)
        else:
            for full in (False, True):
                chart.draw(kind, size, field, full, datasets, products, labels)
        output = ROOT / f"{kind}-{size}-{field}-current.csv"
        with output.open("w", newline="") as stream:
            writer = csv.writer(stream, lineterminator="\n")
            writer.writerow(("product", "operation", "connections", "qps", "error"))
            for product, (results, failures, _) in datasets.items():
                for command, level in sorted(results.keys() | failures.keys()):
                    row = results.get((command, level))
                    writer.writerow((labels[product], command, level,
                                     row["qps"] if row else "",
                                     failures.get((command, level), "")))


if __name__ == "__main__":
    main()
