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

"""Read-only access to Compound File Binary (OLE2) containers.

ArtCAM project files (.art) are Compound File Binary files, the container format documented in
[MS-CFB]. This module implements the subset of the specification needed to list and read the
streams of such a file. It has no dependency on FreeCAD.
"""

import struct

SIGNATURE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"

# Special sector numbers, [MS-CFB] 2.1.
MAX_REGULAR_SECTOR = 0xFFFFFFFA
END_OF_CHAIN = 0xFFFFFFFE
FREE_SECTOR = 0xFFFFFFFF
NO_STREAM = 0xFFFFFFFF

# Directory entry object types, [MS-CFB] 2.6.1.
TYPE_STORAGE = 1
TYPE_STREAM = 2
TYPE_ROOT = 5

HEADER_SIZE = 512
DIRECTORY_ENTRY_SIZE = 128
HEADER_DIFAT_ENTRIES = 109


class CompoundFileError(Exception):
    """The data is not a valid Compound File Binary file."""


class CompoundFile:
    """A Compound File Binary file read entirely into memory.

    Stream paths are tuples of entry names below the root storage, for example
    ``("ArtCAM", "Models", "Model1", "Parameters")``.
    """

    def __init__(self, data):
        if len(data) < HEADER_SIZE or not data.startswith(SIGNATURE):
            raise CompoundFileError("Not a Compound File Binary file")
        self._data = data

        sector_shift, mini_sector_shift = struct.unpack_from("<HH", data, 0x1E)
        if sector_shift not in (9, 12) or mini_sector_shift != 6:
            raise CompoundFileError("Unsupported sector size")
        self._sector_size = 1 << sector_shift
        self._mini_sector_size = 1 << mini_sector_shift

        (
            fat_sector_count,
            first_directory_sector,
            _transaction_signature,
            self._mini_stream_cutoff,
            first_mini_fat_sector,
            _mini_fat_sector_count,
            first_difat_sector,
            difat_sector_count,
        ) = struct.unpack_from("<8I", data, 0x2C)

        self._fat = self._read_fat(fat_sector_count, first_difat_sector, difat_sector_count)
        directory = self._read_chain(first_directory_sector)
        self._entries = self._read_directory(directory)
        if not self._entries or self._entries[0]["type"] != TYPE_ROOT:
            raise CompoundFileError("Missing root directory entry")

        root = self._entries[0]
        self._mini_stream = self._read_chain(root["start"])[: root["size"]]
        self._mini_fat = self._to_sector_list(self._read_chain(first_mini_fat_sector))
        self._paths = {}
        self._collect_paths(root["child"])

    @classmethod
    def from_file(cls, filename):
        """Read the Compound File Binary file at `filename`."""
        with open(filename, "rb") as file:
            return cls(file.read())

    def _sector(self, sector):
        # The header fills sector -1: 512 bytes in version 3, 4096 bytes (zero padded) in version 4.
        start = (sector + 1) * self._sector_size
        if sector > MAX_REGULAR_SECTOR or start + self._sector_size > len(self._data):
            raise CompoundFileError(f"Sector {sector} is outside the file")
        return self._data[start : start + self._sector_size]

    @staticmethod
    def _to_sector_list(data):
        return list(struct.unpack(f"<{len(data) // 4}I", data[: len(data) // 4 * 4]))

    def _read_fat(self, fat_sector_count, difat_sector, difat_sector_count):
        difat = list(struct.unpack_from(f"<{HEADER_DIFAT_ENTRIES}I", self._data, 0x4C))
        entries_per_sector = self._sector_size // 4 - 1
        # The declared count cannot exceed the sectors present in the file, and a DIFAT chain
        # that revisits a sector is malformed.
        physical_sectors = len(self._data) // self._sector_size - 1
        visited = set()
        for _ in range(min(difat_sector_count, physical_sectors)):
            if difat_sector > MAX_REGULAR_SECTOR:
                break
            if difat_sector in visited:
                raise CompoundFileError("Broken DIFAT chain")
            visited.add(difat_sector)
            sector = self._to_sector_list(self._sector(difat_sector))
            difat.extend(sector[:entries_per_sector])
            difat_sector = sector[entries_per_sector]

        fat_sectors = [sector for sector in difat if sector <= MAX_REGULAR_SECTOR]
        fat_sectors = fat_sectors[:fat_sector_count]
        return self._to_sector_list(b"".join(self._sector(sector) for sector in fat_sectors))

    def _follow(self, start, table):
        """Return the sector numbers of the chain beginning at `start`."""
        chain = []
        sector = start
        while sector != END_OF_CHAIN and sector != FREE_SECTOR:
            if sector >= len(table) or len(chain) > len(table):
                raise CompoundFileError("Broken sector chain")
            chain.append(sector)
            sector = table[sector]
        return chain

    def _read_chain(self, start):
        return b"".join(self._sector(sector) for sector in self._follow(start, self._fat))

    def _read_mini_chain(self, start):
        parts = []
        for sector in self._follow(start, self._mini_fat):
            offset = sector * self._mini_sector_size
            parts.append(self._mini_stream[offset : offset + self._mini_sector_size])
        return b"".join(parts)

    def _read_directory(self, directory):
        entries = []
        for offset in range(0, len(directory) - DIRECTORY_ENTRY_SIZE + 1, DIRECTORY_ENTRY_SIZE):
            name_length = struct.unpack_from("<H", directory, offset + 64)[0]
            name_length = min(max(name_length - 2, 0), 62)
            name = directory[offset : offset + name_length].decode("utf-16-le", "replace")
            entry_type = directory[offset + 66]
            left, right, child = struct.unpack_from("<3I", directory, offset + 68)
            start, size = struct.unpack_from("<IQ", directory, offset + 116)
            if self._sector_size == 512:
                # Version 3 files may leave garbage in the high part of the size, [MS-CFB] 2.6.3.
                size &= 0xFFFFFFFF
            entries.append(
                {
                    "name": name,
                    "type": entry_type,
                    "left": left,
                    "right": right,
                    "child": child,
                    "start": start,
                    "size": size,
                }
            )
        return entries

    def _collect_paths(self, root_child):
        """Record the path of every entry below the root storage.

        A single explicit stack covers siblings and children, so deep storage nesting cannot
        exhaust the Python call stack, and the visited set stops malformed trees that loop.
        """
        pending = [(root_child, ())]
        visited = set()
        while pending:
            entry_id, parent = pending.pop()
            if entry_id == NO_STREAM or entry_id in visited or entry_id >= len(self._entries):
                continue
            visited.add(entry_id)
            entry = self._entries[entry_id]
            path = parent + (entry["name"],)
            self._paths[path] = entry_id
            pending.append((entry["left"], parent))
            pending.append((entry["right"], parent))
            if entry["type"] == TYPE_STORAGE:
                pending.append((entry["child"], path))

    def list_streams(self):
        """Return the paths of all streams, sorted."""
        return sorted(
            path
            for path, entry_id in self._paths.items()
            if self._entries[entry_id]["type"] == TYPE_STREAM
        )

    def list_storages(self, parent=()):
        """Return the names of the storages directly below the storage `parent`, sorted."""
        return sorted(
            path[-1]
            for path, entry_id in self._paths.items()
            if len(path) == len(parent) + 1
            and path[:-1] == tuple(parent)
            and self._entries[entry_id]["type"] == TYPE_STORAGE
        )

    def exists(self, path):
        """Return True if a stream or storage exists at `path`."""
        return tuple(path) in self._paths

    def read_stream(self, path):
        """Return the content of the stream at `path`."""
        entry_id = self._paths.get(tuple(path))
        if entry_id is None or self._entries[entry_id]["type"] != TYPE_STREAM:
            raise KeyError("/".join(path))
        entry = self._entries[entry_id]
        if entry["size"] < self._mini_stream_cutoff:
            data = self._read_mini_chain(entry["start"])
        else:
            data = self._read_chain(entry["start"])
        if len(data) < entry["size"]:
            raise CompoundFileError(f"Stream {'/'.join(path)} is truncated")
        return data[: entry["size"]]
