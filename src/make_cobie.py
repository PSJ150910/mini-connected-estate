"""Export a COBie-style handover spreadsheet.

COBie = the standard Excel layout a building contractor hands to the owner at the end
of a project: one sheet per kind of thing (Facility, Floor, Space, Type, Component,
Document). Every row uses OUR official IDs, so it links to everything else.

Run with:  uv run python src/make_cobie.py
Creates:   reports/cobie_handover.xlsx
"""

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import ifcopenshell
import ifcopenshell.util.element
import pandas as pd

db = sqlite3.connect("data/twin.db")
CREATED_BY = (
    "data.team@greenfield.example"  # COBie wants an email for who made each row
)
CREATED_ON = datetime.now(UTC).date().isoformat()


def stamp(table):
    """Every COBie sheet has Name, CreatedBy, CreatedOn as its first columns."""
    table.insert(1, "CreatedBy", CREATED_BY)
    table.insert(2, "CreatedOn", CREATED_ON)
    return table


# Facility: the site
facility = stamp(
    pd.DataFrame(
        [
            {
                "Name": "Greenfield Academy",
                "Category": "School",
                "ProjectName": "Mini Connected Estate",
            }
        ]
    )
)

# Floor and Space: from the BIM model (it knows which floor each room is on)
model = ifcopenshell.open("data/raw/ifc/campus.ifc")
floors, spaces = [], []
for storey in model.by_type("IfcBuildingStorey"):
    building = ifcopenshell.util.element.get_aggregate(storey)
    floor_name = f"{building.Description} {storey.Name}"
    floors.append(
        {"Name": floor_name, "Category": "Floor", "Elevation": storey.Elevation}
    )
    for space in ifcopenshell.util.element.get_decomposition(storey):
        if space.is_a("IfcSpace"):
            area = ifcopenshell.util.element.get_pset(
                space, "Pset_SpaceCommon", "NetPlannedArea"
            )
            spaces.append(
                {
                    "Name": space.Name,
                    "Category": "Room",
                    "FloorName": floor_name,
                    "Description": space.LongName,
                    "NetArea": round(area, 1),
                }
            )
floor_sheet = stamp(pd.DataFrame(floors).sort_values("Name"))
space_sheet = stamp(pd.DataFrame(spaces).sort_values("Name"))

# Type and Component: from the database
assets = pd.read_sql("SELECT * FROM asset ORDER BY id", db)
TYPE_NAMES = {
    "AHU": "Air Handling Unit",
    "BLR": "Gas Boiler",
    "CAL": "Hot Water Calorifier",
    "DB": "Distribution Board",
    "FAP": "Fire Alarm Panel",
    "MTR": "Electricity Meter",
    "PV": "Solar PV Array",
    "LIFT": "Passenger Lift",
}
type_sheet = stamp(
    pd.DataFrame(
        [
            {"Name": name, "Category": code, "AssetType": "Fixed"}
            for code, name in TYPE_NAMES.items()
        ]
    )
)
component_sheet = stamp(
    pd.DataFrame(
        {
            "Name": assets["id"],
            "TypeName": assets["asset_type"].map(TYPE_NAMES),
            "Space": assets["room_id"],
            "Description": assets["name"],
            "TagNumber": assets["id"],
        }
    )
)

# Document: every PDF, and the official ID it belongs to
docs = pd.read_sql(
    """
    SELECT document.id AS File, document.doc_type AS Category, documentlink.entity_id AS RowName,
           documentlink.entity_kind AS kind
    FROM document JOIN documentlink ON documentlink.document_id = document.id
    ORDER BY document.id""",
    db,
)
document_sheet = stamp(
    pd.DataFrame(
        {
            "Name": docs["File"].str.removesuffix(".pdf"),
            "Category": docs["Category"],
            "SheetName": docs["kind"].map(
                {"asset": "Component", "building": "Facility"}
            ),
            "RowName": docs["RowName"],
            "Directory": "data/raw/docs",
            "File": docs["File"],
        }
    )
)

Path("reports").mkdir(exist_ok=True)
with pd.ExcelWriter("reports/cobie_handover.xlsx") as excel:
    for sheet_name, sheet in [
        ("Facility", facility),
        ("Floor", floor_sheet),
        ("Space", space_sheet),
        ("Type", type_sheet),
        ("Component", component_sheet),
        ("Document", document_sheet),
    ]:
        sheet.to_excel(excel, sheet_name=sheet_name, index=False)
        print(f"{sheet_name:10} {len(sheet):3} rows")
print("Saved reports/cobie_handover.xlsx")
