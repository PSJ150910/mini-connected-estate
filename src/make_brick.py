"""Describe the campus in BRICK SCHEMA: a standard "language" for buildings.

Brick writes facts as tiny 3-word sentences called TRIPLES:
    subject      verb (relation)    object
    AHU-02       feeds              Zone AHU-02
    B1-101       isPartOf           Block A
Any Brick-aware software in the world can now understand our campus.

Run with:  uv run python src/make_brick.py
Creates:   data/processed/campus_brick.ttl
"""

import sqlite3

import brickschema
import ifcopenshell
import ifcopenshell.util.element
import pandas as pd
from rdflib import RDF, RDFS, Literal, Namespace

BRICK = Namespace("https://brickschema.org/schema/Brick#")
SITE = Namespace("urn:greenfield-academy#")  # our own names start with this

db = sqlite3.connect("data/twin.db")
g = brickschema.Graph()
g.bind("brick", BRICK)
g.bind("site", SITE)


def node(official_id):
    """'AHU-02' -> site:AHU-02 (a unique name for the thing inside the graph)."""
    return SITE[official_id.replace(" ", "_")]


def add(official_id, brick_class, label):
    g.add((node(official_id), RDF.type, BRICK[brick_class]))
    g.add((node(official_id), RDFS.label, Literal(label)))


# ---------------------------------------------------------------
# 1. PLACES: site > building > floor > room
# ---------------------------------------------------------------
add("GFA", "Site", "Greenfield Academy")
for b in pd.read_sql("SELECT * FROM building", db).itertuples():
    add(b.id, "Building", b.name)
    g.add((node("GFA"), BRICK.hasPart, node(b.id)))

model = ifcopenshell.open("data/raw/ifc/campus.ifc")  # floors come from the BIM model
for space in model.by_type("IfcSpace"):
    storey = ifcopenshell.util.element.get_aggregate(space)
    building = ifcopenshell.util.element.get_aggregate(storey)
    floor_id = f"{building.Description} {storey.Name}"  # "B1 Ground Floor"
    add(floor_id, "Floor", floor_id)
    g.add((node(building.Description), BRICK.hasPart, node(floor_id)))
    add(space.Name, "Room", space.LongName)
    g.add((node(floor_id), BRICK.hasPart, node(space.Name)))

# ---------------------------------------------------------------
# 2. EQUIPMENT, and the room each one is in
# ---------------------------------------------------------------
BRICK_CLASS = {
    "AHU": "AHU",
    "BLR": "Boiler",
    "CAL": "Hot_Water_Storage_Tank",
    "DB": "Electrical_Equipment",  # no exact Brick class for a distribution board yet
    "FAP": "Fire_Alarm_Control_Panel",
    "MTR": "Building_Electrical_Meter",
    "PV": "PV_Array",
    "LIFT": "Elevator",
}
for a in pd.read_sql("SELECT * FROM asset", db).itertuples():
    add(a.id, BRICK_CLASS[a.asset_type], a.name)
    g.add((node(a.id), BRICK.hasLocation, node(a.room_id)))

# ---------------------------------------------------------------
# 3. WHICH AIR HANDLER FEEDS WHICH ROOMS (from the mechanical drawings)
#    AHU -> feeds -> HVAC zone -> hasPart -> rooms
# ---------------------------------------------------------------
FEEDS = {
    "AHU-01": ["B1-101", "B1-102", "B1-103"],  # Block A ground floor
    "AHU-02": ["B1-105", "B1-106", "B1-107"],  # Block A first floor
    "AHU-03": ["B2-201", "B2-202", "B2-203", "B2-204", "B2-205"],
    "AHU-04": ["B3-301", "B3-302", "B3-303", "B3-304"],
}
for ahu, room_ids in FEEDS.items():
    zone = f"Zone {ahu}"
    add(zone, "HVAC_Zone", f"Rooms served by {ahu}")
    g.add((node(ahu), BRICK.feeds, node(zone)))
    for room_id in room_ids:
        g.add((node(zone), BRICK.hasPart, node(room_id)))

# ---------------------------------------------------------------
# 4. SENSORS (BMS points): what they measure, and what they belong to
# ---------------------------------------------------------------
SENSOR_CLASS = {
    "ZoneTemp": "Zone_Air_Temperature_Sensor",
    "CO2": "CO2_Level_Sensor",
    "Occ": "Occupancy_Count_Sensor",
    "SAT": "Supply_Air_Temperature_Sensor",
    "FanStatus": "Fan_Status",
    "kWh": "Energy_Sensor",
}
for s in pd.read_sql("SELECT * FROM sensor", db).fillna("").itertuples():
    add(s.id, SENSOR_CLASS[s.measure], s.id)
    owner = s.room_id or s.asset_id
    g.add((node(s.id), BRICK.isPointOf, node(owner)))

g.serialize("data/processed/campus_brick.ttl", format="turtle")
print(f"Saved data/processed/campus_brick.ttl with {len(g)} triples")

# ---------------------------------------------------------------
# 5. ASK A QUESTION IN SPARQL (the SQL of graphs)
#    "Which temperature sensors are in rooms fed by AHU-02?"
# ---------------------------------------------------------------
question = """
SELECT ?room ?sensor WHERE {
    site:AHU-02 brick:feeds ?zone .
    ?zone brick:hasPart ?room .
    ?sensor brick:isPointOf ?room .
    ?sensor a brick:Zone_Air_Temperature_Sensor .
}
ORDER BY ?room
"""
print("\nTemperature sensors in rooms fed by AHU-02:")
for room, sensor in g.query(question):
    print(f"  {room.split('#')[1]:8} {sensor.split('#')[1]}")
