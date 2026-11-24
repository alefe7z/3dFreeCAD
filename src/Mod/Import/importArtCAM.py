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

"""Import the toolpath geometry of ArtCAM project files (.art).

Each toolpath becomes a Part feature holding its contours as wires of lines and arcs, placed in
a group named after the file. See artcam/reader.py for what the reader can recover.
"""

import os

import FreeCAD
import Part

from artcam import reader
from artcam.cfb import CompoundFileError

translate = FreeCAD.Qt.translate

PROPERTY_GROUP = "ArtCAM"


def open(filename):
    """Create a new document and import the ArtCAM file `filename` into it."""
    docname = os.path.splitext(os.path.basename(filename))[0]
    document = FreeCAD.newDocument(docname)
    document.Label = docname
    import_file(filename, document)
    return document


def insert(filename, docname):
    """Import the ArtCAM file `filename` into the document `docname`, creating it if needed."""
    try:
        document = FreeCAD.getDocument(docname)
    except NameError:
        document = FreeCAD.newDocument(docname)
    FreeCAD.ActiveDocument = document
    import_file(filename, document)
    return document


def import_file(filename, document):
    """Import the toolpaths of the ArtCAM file `filename` into `document`.

    Return the group containing the created objects.
    """
    try:
        project = reader.read(filename)
    except (reader.ArtCAMError, CompoundFileError, OSError) as error:
        FreeCAD.Console.PrintError(
            translate("ImportArtCAM", "Cannot read the ArtCAM file {}: {}").format(filename, error)
            + "\n"
        )
        return None

    group = document.addObject("App::DocumentObjectGroup", "ArtCAM")
    group.Label = os.path.splitext(os.path.basename(filename))[0]

    for toolpath in project.toolpaths:
        shape = make_shape(toolpath)
        if shape is None:
            continue
        feature = document.addObject("Part::Feature", "Toolpath")
        feature.Label = toolpath.name or toolpath.identifier
        feature.Shape = shape
        feature.addProperty(
            "App::PropertyString",
            "Tool",
            PROPERTY_GROUP,
            "The tool of the ArtCAM toolpath",
        )
        feature.Tool = toolpath.tool
        group.addObject(feature)
        if toolpath.skipped_contours:
            FreeCAD.Console.PrintWarning(
                translate(
                    "ImportArtCAM", "ArtCAM toolpath {}: {} contours could not be read"
                ).format(feature.Label, toolpath.skipped_contours)
                + "\n"
            )

    if project.has_vectors:
        FreeCAD.Console.PrintMessage(
            translate(
                "ImportArtCAM",
                "ArtCAM design vectors are stored encrypted and were not imported. "
                "The imported contours are the toolpaths, which follow the tool center.",
            )
            + "\n"
        )
    if project.relief and project.relief.max_height != project.relief.min_height:
        FreeCAD.Console.PrintWarning(
            translate("ImportArtCAM", "ArtCAM reliefs are not supported and were not imported.")
            + "\n"
        )

    document.recompute()
    return group


def make_shape(toolpath):
    """Return a compound of the toolpath contours, or None if it has no geometry."""
    wires = []
    for contour in toolpath.contours:
        edges = [edge for edge in (make_edge(span) for span in contour.spans) if edge]
        if not edges:
            continue
        try:
            wires.append(Part.Wire(edges))
        except Part.OCCError:
            # Contours that are not connected within tolerance are kept as separate edges.
            wires.extend(edges)
    if not wires:
        return None
    return Part.Compound(wires)


def make_edge(span):
    """Return the edge of a line or arc span, or None for a degenerate span."""
    start = FreeCAD.Vector(span.start[0], span.start[1], 0.0)
    end = FreeCAD.Vector(span.end[0], span.end[1], 0.0)
    if start.isEqual(end, Part.Precision.confusion()):
        return None
    if span.is_arc():
        middle = span.midpoint()
        try:
            return Part.Arc(start, FreeCAD.Vector(middle[0], middle[1], 0.0), end).toShape()
        except Part.OCCError:
            # An arc too flat to construct is replaced by its chord.
            pass
    return Part.LineSegment(start, end).toShape()
