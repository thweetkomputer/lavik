#!/usr/bin/env python3
"""Render one self-contained SVG per String size from results.csv."""

import csv
from html import escape
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SIZES = {2048: "2K", 4096: "4K", 8192: "8K", 32768: "32K",
         131072: "128K", 1048576: "1M"}
COLORS = {"Redis": "#dc5038", "Valkey": "#d9901f", "Lavik": "#2367bb",
          "Lavik serial": "#697486", "Lavik before cleaner": "#697486"}
ORDER = ("Redis", "Valkey", "Lavik serial", "Lavik before cleaner", "Lavik")
BEFORE = {"Lavik serial", "Lavik before cleaner"}


def line(x1, y1, x2, y2, color, width=1, extra=""):
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" '
            f'y2="{y2:.1f}" stroke="{color}" stroke-width="{width}" {extra}/>')


def label(x, y, value, size=16, anchor="start", color="#263247", weight=400):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" '
            f'text-anchor="{anchor}" fill="{color}" font-weight="{weight}">'
            f'{escape(str(value))}</text>')


def panel(rows, kind, top, pieces):
    left, right, height = 105, 1110, 255
    bottom = top + height
    x_values = sorted({int(row["connections"]) for row in rows})
    peak = max(float(row["qps"]) for row in rows if row["operation"] == kind)
    step = 10 ** math.floor(math.log10(peak / 4))
    for factor in (1, 2, 5, 10):
        if peak / (factor * step) <= 5:
            step *= factor
            break
    ceiling = math.ceil(peak / step) * step
    pieces.append(label(left, top - 17, kind + " · QPS", 21, weight=700))
    for i in range(int(ceiling // step) + 1):
        value = i * step
        y = bottom - value / ceiling * height
        pieces.append(line(left, y, right, y, "#dfe5ed", 1))
        tick = f"{value:,.0f}" if ceiling < 10000 else f"{value/1000:,.0f}k"
        pieces.append(label(left - 12, y + 5, tick, 14,
                            "end", "#66758b"))
    for index, connections in enumerate(x_values):
        x = left + index * (right - left) / max(1, len(x_values) - 1)
        pieces.append(line(x, top, x, bottom, "#edf1f5", 1))
        pieces.append(label(x, bottom + 25, connections, 14, "middle",
                            "#66758b"))
    pieces.append(label((left + right) / 2, bottom + 55,
                        "Connections (tested levels)", 16,
                        "middle", "#52627a"))
    for product in ORDER:
        points = sorted(((int(row["connections"]), float(row["qps"]))
                         for row in rows if row["operation"] == kind and
                         row["product"] == product))
        if not points:
            continue
        coordinates = [(left + x_values.index(x) * (right - left) /
                        max(1, len(x_values) - 1),
                        bottom - y / ceiling * height) for x, y in points]
        dash = 'stroke-dasharray="8 5"' if product in BEFORE else ""
        path = " ".join(f"{x:.1f},{y:.1f}" for x, y in coordinates)
        pieces.append(f'<polyline points="{path}" fill="none" '
                      f'stroke="{COLORS[product]}" stroke-width="3" {dash}/>')
        for x, y in coordinates:
            pieces.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" '
                          f'fill="{COLORS[product]}"/>')


def render(size, rows):
    pieces = ['<svg xmlns="http://www.w3.org/2000/svg" '
              'viewBox="0 0 1200 885" role="img">',
              '<rect width="1200" height="885" fill="#ffffff"/>',
              label(105, 52, f"{SIZES[size]} String · throughput by connections",
                    29, weight=700),
              label(105, 78, "8 GiB logical data · 16 client threads · pipeline 1 · 15 s per point",
                    15, color="#66758b")]
    x = 105
    for product in ORDER:
        if not any(row["product"] == product for row in rows):
            continue
        pieces.append(line(x, 110, x + 28, 110, COLORS[product], 3,
                           'stroke-dasharray="8 5"' if product in BEFORE else ""))
        pieces.append(label(x + 36, 115, product, 15))
        x += max(178, 50 + len(product) * 9)
    panel(rows, "GET", 170, pieces)
    panel(rows, "SET", 535, pieces)
    pieces.append('</svg>')
    output = ROOT / "charts" / f"{SIZES[size]}.svg"
    output.parent.mkdir(exist_ok=True)
    output.write_text("\n".join(pieces) + "\n")
    print(output)


def main():
    with (ROOT / "results.csv").open(newline="") as handle:
        data = list(csv.DictReader(handle))
    for size in SIZES:
        rows = [row for row in data if int(row["size_bytes"]) == size]
        assert rows and {row["operation"] for row in rows} == {"GET", "SET"}
        render(size, rows)


if __name__ == "__main__":
    main()
