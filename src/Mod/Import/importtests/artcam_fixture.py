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

"""Build a small synthetic ArtCAM project file for the ArtCAM import tests.

The streams follow the layout that artcam/reader.py decodes from ArtCAM Pro 2008 files. They are
written into a minimal Compound File Binary container (version 3, every stream in the mini
stream). This module has no dependency on FreeCAD.
"""

import math
import struct

SECTOR_SIZE = 512
MINI_SECTOR_SIZE = 64
END_OF_CHAIN = 0xFFFFFFFE
FREE_SECTOR = 0xFFFFFFFF
FAT_SECTOR = 0xFFFFFFFD
NO_STREAM = 0xFFFFFFFF

# A clockwise quarter arc has a bulge of -tan(22.5 degrees).
QUARTER_ARC_BULGE = math.tan(math.pi / 8.0)


def utf16_string(text):
    """Encode `text` as a 32-bit character count followed by UTF-16 text."""
    return struct.pack("<I", len(text)) + text.encode("utf-16-le")


def version_stream():
    return struct.pack("<6i", 9, 1, 1, 2008, 151, 32) + utf16_string("ArtCAM 2008.151 Unicode")


def toolpath_list_stream(identifiers):
    data = struct.pack("<HH", 1, len(identifiers))
    for identifier in identifiers:
        data += struct.pack("<H", len(identifier)) + identifier.encode("ascii")
    return data


def parameters_stream(tool, name):
    return b"\x0a\x00\x04\x00" + b"\x00" * 64 + utf16_string(tool) + utf16_string(name) + b"\0" * 8


def line(start, end):
    return struct.pack("<ii4d", 0, 0, *start, *end)


def arc(start, end, bulge):
    return struct.pack("<ii6d", 1, 2, *start, *end, bulge, 1.0e-4)


def start_span(point):
    return struct.pack("<ii4di", 0, 13, *point, *point, 1)


def contour(closed, spans, identifier):
    header = struct.pack("<3i2d", 6, 1, 1 if closed else 0, 1.0e-5, 0.0)
    return header + struct.pack("<Iii", identifier, -1, len(spans)) + b"".join(spans)


def data2_stream(class_name, contours):
    name = class_name.encode("ascii")
    header = struct.pack("<iHiii", 3, 0, 1, 1, 1) + b"\0" * 12
    header += b"\xff\xff\x01\x00" + struct.pack("<H", len(name)) + name
    header += struct.pack("<3i2d4ii", 1, 0, 0, 1.0e-3, 1.0e-2, 2, 1, 0, 1, 1) + struct.pack(
        "<d", -1.0
    )
    header += struct.pack("<4i", 2, 0, 1, len(contours))
    return header + b"".join(contours) + b"\0" * 16


def rounded_rectangle(width, height, radius):
    """Return the spans of a clockwise rectangle with rounded corners, from the origin corner."""
    w, h, r = width, height, radius
    return [
        line((0.0, r), (0.0, h - r)),
        arc((0.0, h - r), (r, h), -QUARTER_ARC_BULGE),
        line((r, h), (w - r, h)),
        arc((w - r, h), (w, h - r), -QUARTER_ARC_BULGE),
        line((w, h - r), (w, r)),
        arc((w, r), (w - r, 0.0), -QUARTER_ARC_BULGE),
        line((w - r, 0.0), (r, 0.0)),
        arc((r, 0.0), (0.0, r), -QUARTER_ARC_BULGE),
    ]


def relief_stream(width, height):
    lines = [
        "  Relief  RELIEF FILE   Relief",
        "  Relief is 100 pixels wide by 50 pixels high",
        f"  In real units the relief is {width:.2f}mm wide by {height:.2f}mm high",
        "  Maximum height in the relief is 0.00mm, minimum height is 0.00mm",
        "  Position of the relief is X:0.000mm Y:0.000mm Z:0.000mm",
    ]
    return ("\r\n" + "\r\n".join(lines) + "\r\n").encode("latin-1") + b"\0" * 64


def project_streams():
    """Return the streams of the fixture project, as a dictionary of path tuples to bytes.

    The project has two toolpaths: "Profile", one closed 20 mm x 10 mm rectangle with 2 mm
    corner radii, and "Engrave", one open contour of two lines.
    """
    profile_id = "ProfileToolpathIdentifier01"
    engrave_id = "EngraveToolpathIdentifier02"
    toolpaths = ("ArtCAM", "ToolpathData")
    profile = contour(True, rounded_rectangle(20.0, 10.0, 2.0), 100)
    engrave = contour(
        False,
        [start_span((5.0, 5.0)), line((5.0, 5.0), (15.0, 5.0)), line((15.0, 5.0), (15.0, 8.0))],
        101,
    )
    return {
        ("ArtCAM", "VersionInfo", "VersionA"): version_stream(),
        ("ArtCAM", "Reliefs", "Relief1"): relief_stream(20.0, 10.0),
        toolpaths + ("#ToolpathList",): toolpath_list_stream([profile_id, engrave_id]),
        toolpaths + (profile_id, "Parameters"): parameters_stream("End Mill 4mm", "Profile"),
        toolpaths + (profile_id, "Data2"): data2_stream("tpmContourGroupDrivePicture", [profile]),
        toolpaths + (engrave_id, "Parameters"): parameters_stream("V-Bit 60deg", "Engrave"),
        toolpaths
        + (engrave_id, "Data2"): data2_stream("tpmOpenContourGroupDrivePicture", [engrave]),
    }


def build_compound_file(streams):
    """Return a Compound File Binary file containing `streams`, all smaller than 4096 bytes."""
    # Directory entries: the root, then each storage and stream, in path order.
    entries = [{"name": "Root Entry", "type": 5, "children": []}]
    index = {(): 0}
    for path in sorted(streams):
        for depth in range(1, len(path) + 1):
            prefix = path[:depth]
            if prefix in index:
                continue
            is_stream = depth == len(path)
            index[prefix] = len(entries)
            entries.append({"name": prefix[-1], "type": 2 if is_stream else 1, "children": []})
            entries[index[prefix[:-1]]]["children"].append(index[prefix])

    # The mini stream holds every stream, each starting on a mini sector boundary.
    mini_stream = b""
    mini_fat = []
    for path, data in sorted(streams.items()):
        if len(data) >= 4096:
            raise ValueError("Only streams smaller than 4096 bytes are supported")
        entry = entries[index[path]]
        sectors = max(1, -(-len(data) // MINI_SECTOR_SIZE))
        entry["start"] = len(mini_fat)
        entry["size"] = len(data)
        mini_fat.extend(range(len(mini_fat) + 1, len(mini_fat) + sectors))
        mini_fat.append(END_OF_CHAIN)
        mini_stream += data.ljust(sectors * MINI_SECTOR_SIZE, b"\0")

    def sector_count(size):
        return max(1, -(-size // SECTOR_SIZE))

    directory_sectors = sector_count(len(entries) * 128)
    mini_fat_sectors = sector_count(len(mini_fat) * 4)
    mini_stream_sectors = sector_count(len(mini_stream))
    content_sectors = directory_sectors + mini_fat_sectors + mini_stream_sectors
    fat_sectors = 1
    while fat_sectors * SECTOR_SIZE // 4 < fat_sectors + content_sectors:
        fat_sectors += 1

    # Sector layout: FAT, directory, mini FAT, mini stream.
    fat = [FAT_SECTOR] * fat_sectors
    starts = []
    for count in (directory_sectors, mini_fat_sectors, mini_stream_sectors):
        starts.append(len(fat))
        fat.extend(range(len(fat) + 1, len(fat) + count))
        fat.append(END_OF_CHAIN)
    first_directory, first_mini_fat, first_mini_stream = starts
    fat.extend([FREE_SECTOR] * (fat_sectors * SECTOR_SIZE // 4 - len(fat)))

    entries[0]["start"] = first_mini_stream
    entries[0]["size"] = len(mini_stream)

    # Link the children of each storage as a chain of right siblings, in the required order.
    for entry in entries:
        entry.setdefault("left", NO_STREAM)
        entry.setdefault("right", NO_STREAM)
        children = sorted(
            entry["children"],
            key=lambda child: (len(entries[child]["name"]), entries[child]["name"].upper()),
        )
        entry["child"] = children[0] if children else NO_STREAM
        for current, following in zip(children, children[1:]):
            entries[current]["right"] = following

    directory = b""
    for entry in entries:
        name = entry["name"].encode("utf-16-le") + b"\0\0"
        directory += name.ljust(64, b"\0")
        directory += struct.pack(
            "<HBB3I", len(name), entry["type"], 1, entry["left"], entry["right"], entry["child"]
        )
        directory += b"\0" * 36
        directory += struct.pack("<IQ", entry.get("start", 0), entry.get("size", 0))

    header = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\0" * 16
    header += struct.pack("<HHHHH", 0x3E, 3, 0xFFFE, 9, 6) + b"\0" * 10
    header += struct.pack(
        "<8I",
        fat_sectors,
        first_directory,
        0,  # Transaction signature.
        4096,  # Mini stream cutoff size.
        first_mini_fat,
        mini_fat_sectors,
        END_OF_CHAIN,  # No DIFAT sectors.
        0,
    )
    difat = list(range(fat_sectors)) + [FREE_SECTOR] * (109 - fat_sectors)
    header += struct.pack("<109I", *difat)

    def padded(data, sectors):
        return data.ljust(sectors * SECTOR_SIZE, b"\0")

    mini_fat += [FREE_SECTOR] * (mini_fat_sectors * SECTOR_SIZE // 4 - len(mini_fat))
    return b"".join(
        (
            header,
            struct.pack(f"<{len(fat)}I", *fat),
            padded(directory, directory_sectors),
            struct.pack(f"<{len(mini_fat)}I", *mini_fat),
            padded(mini_stream, mini_stream_sectors),
        )
    )


def write_project(filename):
    """Write the fixture ArtCAM project to `filename`."""
    with open(filename, "wb") as file:
        file.write(build_compound_file(project_streams()))
