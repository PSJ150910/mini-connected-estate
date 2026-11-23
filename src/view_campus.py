"""Draw the campus IFC model in 3D with matplotlib (no BIM software needed).

Run with:  uv run python src/view_campus.py
A window opens: drag with the mouse to rotate. Close it to finish.
Also saves:  reports/campus_3d.png

We read each box's outline, height and position straight from the IFC file
and draw it ourselves, so we don't need IfcOpenShell's 3D engine.
"""

from pathlib import Path

import ifcopenshell
import ifcopenshell.util.placement
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

model = ifcopenshell.open("data/raw/ifc/campus.ifc")

# Colour for each kind of object: (red, green, blue, see-through amount)
COLOURS = {
    "IfcSpace": (0.3, 0.6, 1.0, 0.15),  # rooms: light blue, see-through
    "IfcSlab": (0.6, 0.6, 0.6, 0.7),  # floors: grey
}
EQUIPMENT_COLOUR = (0.9, 0.3, 0.2, 1.0)  # machines: solid red


def box_faces(product):
    """Work out the faces of a product's box shape, in metres."""
    solid = product.Representation.Representations[0].Items[0]
    outline = np.array(solid.SweptArea.OuterCurve.Points.CoordList)  # floor plan
    height = solid.Depth
    # The model stores millimetres; the placement says where the box sits
    matrix = ifcopenshell.util.placement.get_local_placement(product.ObjectPlacement)
    bottom = [matrix @ [x, y, 0, 1] for x, y in outline]
    top = [matrix @ [x, y, height, 1] for x, y in outline]
    bottom = [point[:3] / 1000 for point in bottom]
    top = [point[:3] / 1000 for point in top]
    faces = [bottom, top]
    for i in range(len(outline)):  # one wall face per edge of the outline
        j = (i + 1) % len(outline)
        faces.append([bottom[i], bottom[j], top[j], top[i]])
    return faces


figure = plt.figure(figsize=(12, 6))
axes = figure.add_subplot(projection="3d")

for product in model.by_type("IfcProduct"):
    if not product.Representation:  # skip things with no shape (like storeys)
        continue
    colour = COLOURS.get(product.is_a(), EQUIPMENT_COLOUR)
    axes.add_collection3d(Poly3DCollection(box_faces(product), facecolor=colour))

# Label each building above its roof
for building in model.by_type("IfcBuilding"):
    x = building.ObjectPlacement.RelativePlacement.Location.Coordinates[0] / 1000
    axes.text(x, 3.5, 9, building.Name, fontsize=9)

axes.set_xlim(0, 130)
axes.set_ylim(-30, 40)
axes.set_zlim(0, 20)
axes.set_xlabel("x (m)")
axes.set_ylabel("y (m)")
axes.set_title("Greenfield Academy campus (from campus.ifc)")

Path("reports").mkdir(exist_ok=True)
plt.savefig("reports/campus_3d.png", dpi=120)
print("Saved reports/campus_3d.png. Drag the window to rotate, close it to finish.")
plt.show()
