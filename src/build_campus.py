"""Build a small 3-building school campus as an IFC (BIM) file.

Run with:  uv run python src/build_campus.py
Creates:   data/raw/ifc/campus.ifc
"""

import ifcopenshell
import ifcopenshell.api.aggregate
import ifcopenshell.api.context
import ifcopenshell.api.geometry
import ifcopenshell.api.project
import ifcopenshell.api.pset
import ifcopenshell.api.root
import ifcopenshell.api.spatial
import ifcopenshell.api.unit
import numpy as np

# ---------------------------------------------------------------
# 1. THE CAMPUS DESIGN (plain Python lists, easy to read and edit)
# ---------------------------------------------------------------
BUILDINGS = [
    {
        "id": "B1",
        "name": "Block A - Teaching",
        "x": 0,
        "storeys": [
            [
                "B1-101 Classroom 1",
                "B1-102 Classroom 2",
                "B1-103 Main Hall",
                "B1-104 Plant Room",
            ],
            ["B1-105 Classroom 3", "B1-106 Classroom 4", "B1-107 IT Suite"],
        ],
    },
    {
        "id": "B2",
        "name": "Block B - Science and Library",
        "x": 45,
        "storeys": [
            ["B2-201 Science Lab", "B2-202 Library", "B2-203 Prep Room"],
            ["B2-204 Art Room", "B2-205 Music Room", "B2-206 Plant Room"],
        ],
    },
    {
        "id": "B3",
        "name": "Block C - Admin and Staff",
        "x": 90,
        "storeys": [
            [
                "B3-301 Staff Room",
                "B3-302 Reception",
                "B3-303 Head Office",
                "B3-304 Canteen",
                "B3-305 Plant Room",
            ],
        ],
    },
]

# Equipment: (tag, IFC class, predefined type, room it sits in, description)
# fmt: off
EQUIPMENT = [
    ("AHU-01", "IfcUnitaryEquipment", "AIRHANDLER", "B1-104", "Air handling unit, ground floor"),
    ("AHU-02", "IfcUnitaryEquipment", "AIRHANDLER", "B1-104", "Air handling unit, first floor"),
    ("AHU-03", "IfcUnitaryEquipment", "AIRHANDLER", "B2-206", "Air handling unit, Block B"),
    ("AHU-04", "IfcUnitaryEquipment", "AIRHANDLER", "B3-305", "Air handling unit, Block C"),
    ("BLR-01", "IfcBoiler", "WATER", "B1-104", "Gas boiler"),
    ("BLR-02", "IfcBoiler", "WATER", "B2-206", "Gas boiler"),
    ("BLR-03", "IfcBoiler", "WATER", "B3-305", "Gas boiler"),
    ("CAL-01", "IfcTank", "STORAGE", "B1-104", "Hot water calorifier"),
    ("CAL-02", "IfcTank", "STORAGE", "B3-305", "Hot water calorifier"),
    ("DB-01", "IfcElectricDistributionBoard", "DISTRIBUTIONBOARD", "B1-104", "Main distribution board"),
    ("DB-02", "IfcElectricDistributionBoard", "DISTRIBUTIONBOARD", "B2-206", "Distribution board"),
    ("DB-03", "IfcElectricDistributionBoard", "DISTRIBUTIONBOARD", "B3-305", "Distribution board"),
    ("FAP-01", "IfcAlarm", "USERDEFINED", "B1-101", "Fire alarm panel"),
    ("FAP-02", "IfcAlarm", "USERDEFINED", "B2-202", "Fire alarm panel"),
    ("FAP-03", "IfcAlarm", "USERDEFINED", "B3-302", "Fire alarm panel"),
    ("MTR-01", "IfcFlowMeter", "ENERGYMETER", "B1-104", "Electricity meter"),
    ("MTR-02", "IfcFlowMeter", "ENERGYMETER", "B2-206", "Electricity meter"),
    ("MTR-03", "IfcFlowMeter", "ENERGYMETER", "B3-305", "Electricity meter"),
    ("PV-01", "IfcSolarDevice", "SOLARPANEL", "B3-305", "Rooftop solar array"),
    ("LIFT-01", "IfcTransportElement", "ELEVATOR", "B1-103", "Passenger lift"),
]
# fmt: on

ROOM_W, ROOM_D, STOREY_H = 8.0, 7.0, 3.5  # metres

# ---------------------------------------------------------------
# 2. CREATE AN EMPTY IFC FILE WITH A PROJECT, UNITS AND A 3D CONTEXT
# ---------------------------------------------------------------
model = ifcopenshell.api.project.create_file(version="IFC4")
project = ifcopenshell.api.root.create_entity(
    model, ifc_class="IfcProject", name="Mini Connected Estate"
)
ifcopenshell.api.unit.assign_unit(model)  # sets the model's units
context = ifcopenshell.api.context.add_context(model, context_type="Model")
body = ifcopenshell.api.context.add_context(
    model,
    context_type="Model",
    context_identifier="Body",
    target_view="MODEL_VIEW",
    parent=context,
)


def place(product, x, y, z):
    """Move a product to position x, y, z (in metres)."""
    matrix = np.eye(4)
    matrix[:, 3] = [x, y, z, 1]
    ifcopenshell.api.geometry.edit_object_placement(
        model, product=product, matrix=matrix
    )


def give_box_shape(product, length, width, height):
    """Give a product a simple box shape so viewers can draw it."""
    shape = ifcopenshell.api.geometry.add_wall_representation(
        model, context=body, length=length, height=height, thickness=width
    )
    ifcopenshell.api.geometry.assign_representation(
        model, product=product, representation=shape
    )


# ---------------------------------------------------------------
# 3. BUILD THE FAMILY TREE: site > buildings > storeys > rooms
# ---------------------------------------------------------------
site = ifcopenshell.api.root.create_entity(
    model, ifc_class="IfcSite", name="Greenfield Academy"
)
ifcopenshell.api.aggregate.assign_object(
    model, products=[site], relating_object=project
)

rooms = {}  # room id -> (IfcSpace, x, y, z), so equipment can find its room later

for b in BUILDINGS:
    building = ifcopenshell.api.root.create_entity(
        model, ifc_class="IfcBuilding", name=b["name"]
    )
    building.Description = b["id"]
    ifcopenshell.api.aggregate.assign_object(
        model, products=[building], relating_object=site
    )
    place(building, b["x"], 0, 0)

    for level, room_list in enumerate(b["storeys"]):
        storey_name = "Ground Floor" if level == 0 else f"Floor {level}"
        storey = ifcopenshell.api.root.create_entity(
            model, ifc_class="IfcBuildingStorey", name=storey_name
        )
        storey.Elevation = level * STOREY_H
        ifcopenshell.api.aggregate.assign_object(
            model, products=[storey], relating_object=building
        )
        place(storey, b["x"], 0, level * STOREY_H)

        # A floor slab under the whole storey
        slab = ifcopenshell.api.root.create_entity(
            model, ifc_class="IfcSlab", name=f"{b['id']} {storey_name} slab"
        )
        ifcopenshell.api.spatial.assign_container(
            model, products=[slab], relating_structure=storey
        )
        give_box_shape(slab, len(room_list) * ROOM_W, ROOM_D, 0.2)
        place(slab, b["x"], 0, level * STOREY_H - 0.2)

        for i, label in enumerate(room_list):
            room_id, room_name = label.split(" ", 1)
            space = ifcopenshell.api.root.create_entity(
                model, ifc_class="IfcSpace", name=room_id
            )
            space.LongName = room_name
            ifcopenshell.api.aggregate.assign_object(
                model, products=[space], relating_object=storey
            )
            give_box_shape(space, ROOM_W - 0.2, ROOM_D - 0.2, STOREY_H - 0.3)
            x, y, z = b["x"] + i * ROOM_W + 0.1, 0.1, level * STOREY_H
            place(space, x, y, z)
            pset = ifcopenshell.api.pset.add_pset(
                model, product=space, name="Pset_SpaceCommon"
            )
            ifcopenshell.api.pset.edit_pset(
                model,
                pset=pset,
                properties={"NetPlannedArea": (ROOM_W - 0.2) * (ROOM_D - 0.2)},
            )
            rooms[room_id] = (space, x, y, z)

# ---------------------------------------------------------------
# 4. PUT EQUIPMENT INSIDE ROOMS
# ---------------------------------------------------------------
count_in_room = {}
for tag, ifc_class, ptype, room_id, description in EQUIPMENT:
    item = ifcopenshell.api.root.create_entity(
        model, ifc_class=ifc_class, predefined_type=ptype, name=tag
    )
    item.Tag = tag
    item.Description = description
    if ptype == "USERDEFINED":
        item.ObjectType = description
    space, x, y, z = rooms[room_id]
    ifcopenshell.api.spatial.assign_container(
        model, products=[item], relating_structure=space
    )

    # Line items up in rows of 5 inside the room, 1.5 m apart
    n = count_in_room.get(room_id, 0)
    count_in_room[room_id] = n + 1
    column, row = n % 5, n // 5
    give_box_shape(item, 1.0, 1.0, 1.5)
    place(item, x + 0.3 + column * 1.5, y + 0.5 + row * 2.0, z)

model.write("data/raw/ifc/campus.ifc")
print(
    f"Saved campus.ifc with {len(rooms)} rooms and {len(EQUIPMENT)} pieces of equipment"
)