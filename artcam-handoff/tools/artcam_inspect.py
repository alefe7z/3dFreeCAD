#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Inspect an ArtCAM .art file with the FreeCAD-independent reader, optionally writing an SVG.

Coordination tool for agents (see artcam-handoff/README.md); not part of FreeCAD.

    python3 artcam-handoff/tools/artcam_inspect.py file.art [--streams] [--svg out.svg]
"""

import argparse
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "src", "Mod", "Import"))

from artcam import reader  # noqa: E402
from artcam.cfb import CompoundFile  # noqa: E402

COLORS = ["#d33", "#36c", "#2a2", "#c80", "#909", "#088", "#555", "#a52", "#05a", "#6a0"]


def span_points(span, segments=16):
    if not span.is_arc():
        return [span.start, span.end]
    (x1, y1), (x2, y2) = span.start, span.end
    angle = 4.0 * math.atan(span.bulge)
    chord = math.hypot(x2 - x1, y2 - y1)
    radius = chord / (2.0 * math.sin(angle / 2.0))
    distance = radius * math.cos(angle / 2.0)
    cx = (x1 + x2) / 2.0 - (y2 - y1) / chord * distance
    cy = (y1 + y2) / 2.0 + (x2 - x1) / chord * distance
    a0 = math.atan2(y1 - cy, x1 - cx)
    r = abs(radius)
    return [
        (cx + r * math.cos(a0 + angle * i / segments), cy + r * math.sin(a0 + angle * i / segments))
        for i in range(segments + 1)
    ]


def write_svg(project, filename, size=900):
    paths = []
    for index, toolpath in enumerate(project.toolpaths):
        for contour in toolpath.contours:
            points = [p for span in contour.spans for p in span_points(span)]
            if points:
                paths.append((COLORS[index % len(COLORS)], points))
    if not paths:
        print("no geometry")
        return
    xs = [x for _, pts in paths for x, _ in pts]
    ys = [y for _, pts in paths for _, y in pts]
    x0, y1 = min(xs), max(ys)
    scale = size / max(max(xs) - x0, y1 - min(ys), 1e-9)
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{(max(xs) - x0) * scale + 20:.0f}" '
        f'height="{(y1 - min(ys)) * scale + 20:.0f}"><rect width="100%" height="100%" fill="white"/>'
    ]
    for color, pts in paths:
        coords = " ".join(
            f"{(x - x0) * scale + 10:.2f},{(y1 - y) * scale + 10:.2f}" for x, y in pts
        )
        out.append(f'<polyline fill="none" stroke="{color}" stroke-width="0.6" points="{coords}"/>')
    out.append("</svg>")
    with open(filename, "w") as file:
        file.write("\n".join(out))
    print(f"SVG written: {filename}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file")
    parser.add_argument("--streams", action="store_true", help="list container streams")
    parser.add_argument("--svg", help="write the toolpath geometry to this SVG file")
    args = parser.parse_args()

    if args.streams:
        container = CompoundFile.from_file(args.file)
        for path in container.list_streams():
            print(f"{len(container.read_stream(path)):9d}  {'/'.join(path)}")

    project = reader.read(args.file)
    print(f"version: {project.version!r}  encrypted vectors present: {project.has_vectors}")
    print(f"relief: {project.relief}")
    for toolpath in project.toolpaths:
        spans = sum(len(contour.spans) for contour in toolpath.contours)
        length = sum(span.length() for contour in toolpath.contours for span in contour.spans)
        print(
            f"  {toolpath.identifier}  {toolpath.name!r:30} tool={toolpath.tool!r:38} "
            f"contours={len(toolpath.contours):5} spans={spans:6} "
            f"skipped={toolpath.skipped_contours} length={length:.1f}mm"
        )
    if args.svg:
        write_svg(project, args.svg)


if __name__ == "__main__":
    main()
