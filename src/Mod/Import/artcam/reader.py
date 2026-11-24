# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2026 The FreeCAD project contributors
# SPDX-FileNotice: Part of the FreeCAD project.

################################################################################
#                                                                              #
#   FreeCAD is free software: you can redistribute it and/or modify            #
#   it under the terms of the GNU Lesser General Public License as             #
#   published by the Free Software Foundation, either version 2.1              #
#   of the License, or (at your option) any later version.                     #
#                                                                              #
#   FreeCAD is distributed in the hope that it will be useful,                 #
#   but WITHOUT ANY WARRANTY; without even the implied warranty                #
#   of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.                    #
#   See the GNU Lesser General Public License for more details.                #
#                                                                              #
#   You should have received a copy of the GNU Lesser General Public           #
#   License along with FreeCAD. If not, see https://www.gnu.org/licenses       #
#                                                                              #
################################################################################

"""Reader for the toolpath geometry stored in ArtCAM project files (.art).

ArtCAM was discontinued and its format is not publicly documented. The layout decoded here was
determined from files written by ArtCAM Pro 2008, and only covers data stored unencrypted:

- ``ArtCAM/ToolpathData/<id>/Data2``: the 2D picture of a toolpath, as contours of line and arc
  spans. The spans follow the tool center, so a profile is offset from the design vectors by
  the tool radius.
- ``ArtCAM/ToolpathData/<id>/Parameters``: the names of the toolpath and of its tool.
- ``ArtCAM/Reliefs/Relief1``: a text header describing the relief size and position.

The design vectors (``ArtCAM/Models/Model1/VectorDocument``) are encrypted and are not read.

All lengths are in millimeters. This module has no dependency on FreeCAD.
"""

import math
import re
import struct
from dataclasses import dataclass, field

from artcam.cfb import CompoundFile

TOOLPATH_STORAGE = ("ArtCAM", "ToolpathData")
VERSION_STREAM = ("ArtCAM", "VersionInfo", "VersionA")
RELIEF_STREAM = ("ArtCAM", "Reliefs", "Relief1")
VECTOR_STREAM = ("ArtCAM", "Models", "Model1", "VectorDocument")

# Each contour starts with this record: object type 6, version 1, then a closed flag (0 or 1).
CONTOUR_START = re.compile(rb"\x06\x00\x00\x00\x01\x00\x00\x00[\x00\x01]\x00\x00\x00")

# Span type codes, the second integer of each span record.
SPAN_LINE = 0
SPAN_ARC = 2
SPAN_START = 13

# Bounds used to reject a misidentified contour.
MAX_COORDINATE = 1.0e6
MAX_SPANS = 10_000_000
MAX_TOLERANCE = 1.0e-2


class ArtCAMError(Exception):
    """The file is not an ArtCAM project that can be read."""


@dataclass
class Span:
    """A line (bulge 0) or circular arc from `start` to `end` in the XY plane.

    The bulge is the tangent of a quarter of the arc's included angle, as in DXF polylines:
    positive for a counterclockwise arc, negative for a clockwise one.
    """

    start: tuple
    end: tuple
    bulge: float = 0.0

    def is_arc(self):
        return abs(self.bulge) > 1.0e-12

    def midpoint(self):
        """Return the point halfway along the span."""
        (x1, y1), (x2, y2) = self.start, self.end
        mid_x, mid_y = (x1 + x2) / 2.0, (y1 + y2) / 2.0
        if not self.is_arc():
            return (mid_x, mid_y)
        chord = math.hypot(x2 - x1, y2 - y1)
        # The arc midpoint lies at the sagitta from the chord, to the right of the chord direction
        # for a counterclockwise arc.
        sagitta = self.bulge * chord / 2.0
        return (mid_x + sagitta * (y2 - y1) / chord, mid_y - sagitta * (x2 - x1) / chord)

    def length(self):
        (x1, y1), (x2, y2) = self.start, self.end
        chord = math.hypot(x2 - x1, y2 - y1)
        if not self.is_arc():
            return chord
        angle = 4.0 * math.atan(abs(self.bulge))
        return chord * angle / (2.0 * math.sin(angle / 2.0))


@dataclass
class Contour:
    closed: bool
    spans: list = field(default_factory=list)


@dataclass
class Toolpath:
    identifier: str
    name: str = ""
    tool: str = ""
    contours: list = field(default_factory=list)
    skipped_contours: int = 0


@dataclass
class Relief:
    width_pixels: int
    height_pixels: int
    width: float
    height: float
    origin: tuple
    min_height: float
    max_height: float


@dataclass
class ArtCAMProject:
    version: str = ""
    toolpaths: list = field(default_factory=list)
    relief: Relief = None
    has_vectors: bool = False


def read(filename):
    """Read the ArtCAM project file at `filename` and return an ArtCAMProject."""
    with open(filename, "rb") as file:
        return read_bytes(file.read())


def read_bytes(data):
    """Read an ArtCAM project from the content of a .art file."""
    container = CompoundFile(data)
    if not container.exists(("ArtCAM",)):
        raise ArtCAMError("The file is a compound file, but not an ArtCAM project")

    project = ArtCAMProject()
    if container.exists(VERSION_STREAM):
        project.version = parse_version(container.read_stream(VERSION_STREAM))
    if container.exists(RELIEF_STREAM):
        project.relief = parse_relief_header(container.read_stream(RELIEF_STREAM))
    project.has_vectors = container.exists(VECTOR_STREAM)

    for identifier in toolpath_order(container):
        storage = TOOLPATH_STORAGE + (identifier,)
        if not container.exists(storage + ("Data2",)):
            continue
        toolpath = Toolpath(identifier)
        if container.exists(storage + ("Parameters",)):
            toolpath.tool, toolpath.name = parse_names(
                container.read_stream(storage + ("Parameters",))
            )
        toolpath.contours, toolpath.skipped_contours = parse_contours(
            container.read_stream(storage + ("Data2",))
        )
        project.toolpaths.append(toolpath)
    return project


def toolpath_order(container):
    """Return the toolpath identifiers in the order of the ArtCAM toolpath list."""
    present = container.list_storages(TOOLPATH_STORAGE)
    listed = []
    list_stream = TOOLPATH_STORAGE + ("#ToolpathList",)
    if container.exists(list_stream):
        # A 16-bit version and count, then each identifier as a 16-bit length and ASCII text.
        data = container.read_stream(list_stream)
        offset = 4
        while offset + 2 <= len(data):
            (length,) = struct.unpack_from("<H", data, offset)
            identifier = data[offset + 2 : offset + 2 + length].decode("latin-1")
            offset += 2 + length
            if identifier in present and identifier not in listed:
                listed.append(identifier)
    return listed + [identifier for identifier in present if identifier not in listed]


def parse_version(data):
    """Return the version text of the application that saved the file, such as 'ArtCAM 2008'."""
    text = data.decode("utf-16-le", "replace")
    match = re.search(r"ArtCAM[ \w.]*?\d[\d.]*", text)
    return match.group(0) if match else ""


def read_utf16_strings(data):
    """Return the strings stored as a 32-bit character count followed by UTF-16 text."""
    strings = []
    pattern = re.compile(rb"(?:[\x20-\x7e\xa0-\xff]\x00){1,255}")
    for match in pattern.finditer(data):
        start = match.start()
        if start < 4:
            continue
        (count,) = struct.unpack_from("<I", data, start - 4)
        if 0 < count <= len(match.group(0)) // 2:
            strings.append(data[start : start + 2 * count].decode("utf-16-le"))
    return strings


def parse_names(data):
    """Return the tool name and the toolpath name from a toolpath Parameters stream."""
    strings = read_utf16_strings(data)
    if len(strings) >= 2:
        return strings[-2], strings[-1]
    if strings:
        return "", strings[-1]
    return "", ""


def parse_contours(data):
    """Return the contours of a toolpath Data2 stream, and the number that could not be read."""
    contours = []
    skipped = 0
    position = 0
    while True:
        match = CONTOUR_START.search(data, position)
        if not match:
            break
        try:
            contour, position = parse_contour(data, match.start())
        except (ValueError, struct.error):
            skipped += 1
            position = match.start() + 1
            continue
        contours.append(contour)
    return contours, skipped


def parse_contour(data, offset):
    """Parse the contour record at `offset`, and return it with the offset following it.

    Layout: type 6, version 1, closed flag, tolerance and a zero (doubles), identifier, flags,
    span count. Each span is two integers (the second is the span type), the start and end points
    (doubles), then the bulge and tolerance for an arc, or 4 more bytes for a start span.
    """
    closed = data[offset + 8] == 1
    tolerance, reserved = struct.unpack_from("<2d", data, offset + 12)
    if not (0.0 < tolerance < MAX_TOLERANCE) or reserved != 0.0:
        raise ValueError("Not a contour record")
    offset += 28
    _identifier, _flags, span_count = struct.unpack_from("<Iii", data, offset)
    offset += 12
    if not 0 < span_count <= MAX_SPANS:
        raise ValueError("Invalid span count")

    contour = Contour(closed)
    for _ in range(span_count):
        _span_flags, span_type = struct.unpack_from("<ii", data, offset)
        x1, y1, x2, y2 = struct.unpack_from("<4d", data, offset + 8)
        offset += 40
        bulge = 0.0
        if span_type == SPAN_ARC:
            bulge, _arc_tolerance = struct.unpack_from("<2d", data, offset)
            offset += 16
        elif span_type == SPAN_START:
            offset += 4
        elif span_type != SPAN_LINE:
            raise ValueError(f"Unknown span type {span_type}")
        values = (x1, y1, x2, y2, bulge)
        if not all(math.isfinite(value) and abs(value) < MAX_COORDINATE for value in values):
            raise ValueError("Invalid span coordinates")
        if (x1, y1) != (x2, y2):
            contour.spans.append(Span((x1, y1), (x2, y2), bulge))
    return contour, offset


def parse_relief_header(data):
    """Return the relief dimensions from the text header of a relief stream, or None."""
    text = data[:1024].decode("latin-1")
    number = r"(-?\d+(?:\.\d+)?)"
    pixels = re.search(rf"Relief is {number} pixels wide by {number} pixels high", text)
    size = re.search(rf"relief is {number}mm wide by {number}mm high", text)
    heights = re.search(
        rf"Maximum height in the relief is {number}mm, minimum height is {number}mm", text
    )
    origin = re.search(rf"Position of the relief is X:{number}mm Y:{number}mm Z:{number}mm", text)
    if not (pixels and size and heights and origin):
        return None
    return Relief(
        width_pixels=int(float(pixels.group(1))),
        height_pixels=int(float(pixels.group(2))),
        width=float(size.group(1)),
        height=float(size.group(2)),
        origin=tuple(float(value) for value in origin.groups()),
        max_height=float(heights.group(1)),
        min_height=float(heights.group(2)),
    )
