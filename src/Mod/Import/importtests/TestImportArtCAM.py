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

"""ArtCAM project import tests."""

import math
import os
import struct

import FreeCAD
import importArtCAM
from artcam import reader
from artcam.cfb import CompoundFile, CompoundFileError
from importtests import artcam_fixture
from importtests.TestImportBase import TestImportBase

# Perimeter of the fixture's 20 mm x 10 mm rectangle with 2 mm corner radii.
PROFILE_LENGTH = 2 * (16.0 + 6.0) + 2 * math.pi * 2.0


class TestImportArtCAM(TestImportBase):
    """Tests for the ArtCAM project importer."""

    def setUp(self):
        super().setUp()
        self.filename = os.path.join(self.temp_dir, "project.art")
        artcam_fixture.write_project(self.filename)

    def test_read_project(self):
        """Read the toolpath names, tools and contours without creating document objects."""
        project = reader.read(self.filename)

        self.assertEqual(project.version, "ArtCAM 2008.151")
        self.assertEqual([toolpath.name for toolpath in project.toolpaths], ["Profile", "Engrave"])
        self.assertEqual(
            [toolpath.tool for toolpath in project.toolpaths], ["End Mill 4mm", "V-Bit 60deg"]
        )
        self.assertEqual(project.relief.width, 20.0)
        self.assertEqual(project.relief.height, 10.0)

        profile, engrave = project.toolpaths
        self.assertEqual(len(profile.contours), 1)
        self.assertTrue(profile.contours[0].closed)
        self.assertEqual([span.is_arc() for span in profile.contours[0].spans], [False, True] * 4)
        length = sum(span.length() for span in profile.contours[0].spans)
        self.assertAlmostEqual(length, PROFILE_LENGTH)

        # The zero-length start span of the open contour is not kept.
        self.assertFalse(engrave.contours[0].closed)
        self.assertEqual(len(engrave.contours[0].spans), 2)

    def test_read_version_4_container(self):
        """Read a container with 4096 byte sectors, whose sector 0 follows a padded header."""
        filename = os.path.join(self.temp_dir, "version4.art")
        artcam_fixture.write_project(filename, version=4)

        project = reader.read(filename)

        self.assertEqual([toolpath.name for toolpath in project.toolpaths], ["Profile", "Engrave"])
        length = sum(span.length() for span in project.toolpaths[0].contours[0].spans)
        self.assertAlmostEqual(length, PROFILE_LENGTH)

    def test_read_deeply_nested_storages(self):
        """Storage nesting deeper than the Python recursion limit is read without recursion."""
        path = ("Storage",) * 1100 + ("Stream",)
        container = CompoundFile(artcam_fixture.build_compound_file({path: b"content"}))

        self.assertEqual(container.list_streams(), [path])
        self.assertEqual(container.read_stream(path), b"content")

    def test_reject_invalid_start_spans(self):
        """A start span must be a single point followed by its marker, and adds no geometry."""
        line = artcam_fixture.line((0.0, 0.0), (10.0, 0.0))
        valid = artcam_fixture.start_span((0.0, 0.0))
        moved = struct.pack("<ii4di", 0, 13, 0.0, 0.0, 5.0, 0.0, 1)
        truncated = valid[:-4]

        contours, skipped = reader.parse_contours(artcam_fixture.contour(False, [valid, line], 1))
        self.assertEqual((len(contours), skipped), (1, 0))
        self.assertEqual(len(contours[0].spans), 1)

        contours, skipped = reader.parse_contours(artcam_fixture.contour(False, [moved, line], 1))
        self.assertEqual((len(contours), skipped), (0, 1))

        # The record ends inside the start span, so its marker is missing.
        contours, skipped = reader.parse_contours(
            artcam_fixture.contour(False, [line, truncated], 1)
        )
        self.assertEqual((len(contours), skipped), (0, 1))

    def test_arc_midpoint(self):
        """A clockwise quarter arc bulges away from the corner center."""
        corner = reader.Span((0.0, 8.0), (2.0, 10.0), -artcam_fixture.QUARTER_ARC_BULGE)
        x, y = corner.midpoint()
        # The arc is centered at (2, 8) with radius 2.
        self.assertAlmostEqual(x, 2.0 - math.sqrt(2.0))
        self.assertAlmostEqual(y, 8.0 + math.sqrt(2.0))

    def test_import_toolpaths(self):
        """Import each toolpath as a Part feature in a group named after the file."""
        group = importArtCAM.import_file(self.filename, self.document)

        self.assertEqual(group.Label, "project")
        self.assertEqual([obj.Label for obj in group.Group], ["Profile", "Engrave"])
        profile, engrave = group.Group
        self.assertEqual(profile.Tool, "End Mill 4mm")
        self.assertEqual(engrave.Tool, "V-Bit 60deg")

        self.assertEqual(len(profile.Shape.Wires), 1)
        wire = profile.Shape.Wires[0]
        self.assertTrue(wire.isClosed())
        self.assertAlmostEqual(wire.Length, PROFILE_LENGTH, places=6)
        curve_types = sorted(edge.Curve.TypeId for edge in wire.Edges)
        self.assertEqual(curve_types, ["Part::GeomCircle"] * 4 + ["Part::GeomLine"] * 4)
        for edge in wire.Edges:
            if edge.Curve.TypeId == "Part::GeomCircle":
                self.assertAlmostEqual(edge.Curve.Radius, 2.0, places=6)

        bound_box = profile.Shape.BoundBox
        self.assertAlmostEqual(bound_box.XMin, 0.0)
        self.assertAlmostEqual(bound_box.YMin, 0.0)
        self.assertAlmostEqual(bound_box.XMax, 20.0)
        self.assertAlmostEqual(bound_box.YMax, 10.0)
        self.assertAlmostEqual(bound_box.ZLength, 0.0)

        self.assertEqual(len(engrave.Shape.Wires), 1)
        self.assertFalse(engrave.Shape.Wires[0].isClosed())
        self.assertAlmostEqual(engrave.Shape.Length, 13.0)

    def test_insert_into_existing_document(self):
        """The insert entry point adds the objects to the named document."""
        importArtCAM.insert(self.filename, self.document.Name)

        labels = sorted(obj.Label for obj in self.document.Objects)
        self.assertEqual(labels, ["Engrave", "Profile", "project"])

    def test_reject_invalid_file(self):
        """A file that is not a compound file creates no objects."""
        filename = os.path.join(self.temp_dir, "invalid.art")
        with open(filename, "wb") as file:
            file.write(b"not an ArtCAM project" * 50)

        with self.assertRaises(CompoundFileError):
            reader.read(filename)
        self.assertIsNone(importArtCAM.import_file(filename, self.document))
        self.assertEqual(self.document.Objects, [])

    def test_invalid_file_creates_no_document(self):
        """Opening or inserting an unreadable file leaves no new document behind."""
        filename = os.path.join(self.temp_dir, "invalid.art")
        with open(filename, "wb") as file:
            file.write(b"not an ArtCAM project" * 50)
        documents = set(FreeCAD.listDocuments())

        self.assertIsNone(importArtCAM.open(filename))
        self.assertIsNone(importArtCAM.insert(filename, "TestImportArtCAMMissing"))

        self.assertEqual(set(FreeCAD.listDocuments()), documents)
