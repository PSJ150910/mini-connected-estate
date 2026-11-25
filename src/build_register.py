"""Build the MASTER REGISTER: the one official list of buildings, rooms and assets.

The BIM model (IFC) is our "source of truth", so its IDs (B1, B1-101, AHU-02)
become the common IDs that every other system gets matched to.

Run with:  uv run python src/build_register.py
Creates:   data/processed/register.csv
"""

from pathlib import Path

import ifcopenshell
import ifcopenshell.util.element
import pandas as pd

model = ifcopenshell.open("data/raw/ifc/campus.ifc")
rows = []

# ---------------------------------------------------------------
# 1. BUILDINGS and ROOMS
# ---------------------------------------------------------------
for building in model.by_type("IfcBuilding"):
    building_id = building.Description  # we stored "B1", "B2", "B3" here in Module 1
    rows.append(
        {
            "id": building_id,
            "kind": "building",
            "name": building.Name,
            "building_id": building_id,
            "room_id": "",
        }
    )

    for space in ifcopenshell.util.element.get_decomposition(building):
        if space.is_a("IfcSpace"):
            rows.append(
                {
                    "id": space.Name,
                    "kind": "room",
                    "name": space.LongName,
                    "building_id": building_id,
                    "room_id": space.Name,
                }
            )

# ---------------------------------------------------------------
# 2. ASSETS (equipment): which room and building is each one in?
# ---------------------------------------------------------------
room_to_building = {r["id"]: r["building_id"] for r in rows if r["kind"] == "room"}

for item in model.by_type("IfcElement"):
    if item.is_a("IfcSlab"):
        continue  # floor slabs are not equipment
    room = ifcopenshell.util.element.get_container(item)  # the IfcSpace it sits in
    rows.append(
        {
            "id": item.Tag,
            "kind": "asset",
            "name": item.Description,
            "building_id": room_to_building[room.Name],
            "room_id": room.Name,
        }
    )

register = pd.DataFrame(rows).sort_values("id").reset_index(drop=True)

# ---------------------------------------------------------------
# 3. EXTRA COLUMNS THAT HELP MATCHING
#    asset_type: AHU-02 -> "AHU"
#    number_overall: AHU-02 is AHU number 2 on the whole campus
#    number_in_building: AHU-02 is AHU number 2 inside its building (B1)
# ---------------------------------------------------------------
is_asset = register["kind"] == "asset"
register["asset_type"] = register["id"].where(is_asset).str.split("-").str[0]
register["number_overall"] = (
    register.loc[is_asset, "id"].str.split("-").str[1].astype("Int64")
)
register["number_in_building"] = (
    register[is_asset].groupby(["building_id", "asset_type"]).cumcount() + 1
).astype("Int64")
register = register.fillna({"asset_type": ""})

Path("data/processed").mkdir(exist_ok=True)
register.to_csv("data/processed/register.csv", index=False)
print(register["kind"].value_counts().to_string())
print(f"Saved data/processed/register.csv with {len(register)} rows")
