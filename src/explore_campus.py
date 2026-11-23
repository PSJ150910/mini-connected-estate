"""List every building, storey, room and piece of equipment in the IFC model.

Run with:  uv run python src/explore_campus.py
"""

import ifcopenshell
import ifcopenshell.util.element

# Open the BIM model we built
model = ifcopenshell.open("data/raw/ifc/campus.ifc")


def children(parent, ifc_class):
    """Return the objects of one IFC class that sit under a parent, sorted."""
    found = []
    for thing in ifcopenshell.util.element.get_decomposition(parent):
        if thing.is_a(ifc_class):
            found.append(thing)
    return sorted(found, key=lambda thing: thing.Name)


# Walk the family tree: building > storey > room > equipment
for building in children(model.by_type("IfcSite")[0], "IfcBuilding"):
    print(f"BUILDING: {building.Name}")
    for storey in children(building, "IfcBuildingStorey"):
        print(f"  STOREY: {storey.Name}")
        for room in children(storey, "IfcSpace"):
            print(f"    ROOM: {room.Name} {room.LongName}")
            for item in ifcopenshell.util.element.get_contained(room):
                print(f"      EQUIPMENT: {item.Name} ({item.is_a()})")

# Count everything, to compare with what a 3D viewer shows
print()
print("Buildings:", len(model.by_type("IfcBuilding")))
print("Storeys:  ", len(model.by_type("IfcBuildingStorey")))
print("Rooms:    ", len(model.by_type("IfcSpace")))
print("Equipment:", len(model.by_type("IfcElement")) - len(model.by_type("IfcSlab")))