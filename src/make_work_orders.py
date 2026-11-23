"""Generate about 300 messy repair jobs (work orders) from the CAFM system.

Run with:  uv run python src/make_work_orders.py
Creates:   data/raw/cafm/work_orders.csv
"""

import random

import pandas as pd
from faker import Faker

random.seed(7)  # fixed seeds = the same "random" jobs every run
Faker.seed(7)
fake = Faker("en_GB")

# ---------------------------------------------------------------
# 1. HOW THE MAINTENANCE TEAM TYPES EACH ASSET'S NAME
#    Real people type names differently every time. This is the mess!
#    BIM tag : list of names people use in the CAFM
# ---------------------------------------------------------------
ASSET_NAMES = {
    "AHU-01": ["Air Handler 1 Blk A", "AHU 1 Block A", "air handling unit 1 - A"],
    "AHU-02": ["Air Handler 2 Blk A", "AHU2 Blk A", "Air handling unit no.2 (Block A)"],
    "AHU-03": ["Air Handler Blk B", "AHU Science Block", "B Block AHU"],
    "AHU-04": ["Air Handler Blk C", "AHU - Admin", "Admin block air handler"],
    "BLR-01": ["Boiler 1 Blk A", "Blk A boiler", "Main Boiler (Teaching)"],
    "BLR-02": ["Boiler Blk B", "Science block boiler", "Boiler B"],
    "BLR-03": ["Boiler Blk C", "Admin Boiler", "boiler - block c"],
    "CAL-01": ["Calorifier Blk A", "HW Cylinder A", "Hot water tank Block A"],
    "CAL-02": ["Calorifier Blk C", "HW Cylinder C", "Kitchen hot water cylinder"],
    "DB-01": ["Main DB Blk A", "Distribution Board A", "DB1"],
    "DB-02": ["DB Blk B", "Distribution Board B", "DB2 Science"],
    "DB-03": ["DB Blk C", "Distribution Board C", "DB3 Admin"],
    "FAP-01": ["Fire Panel Blk A", "Fire alarm panel - Teaching", "FA Panel A"],
    "FAP-02": ["Fire Panel Blk B", "Fire alarm panel Library", "FA Panel B"],
    "FAP-03": ["Fire Panel Blk C", "Fire alarm panel Reception", "FA Panel C"],
    "MTR-01": ["Elec Meter Blk A", "Electricity meter A"],
    "MTR-02": ["Elec Meter Blk B", "Electricity meter B"],
    "MTR-03": ["Elec Meter Blk C", "Electricity meter C"],
    "PV-01": ["Solar Panels", "PV array roof C", "Solar PV inverter"],
    "LIFT-01": ["Lift", "Passenger Lift Blk A", "Main hall lift"],
}

# Problems that can happen to each kind of asset (matched by the start of the tag)
PROBLEMS = {
    "AHU": [
        "Fan noisy",
        "Filter change due",
        "Belt slipping",
        "No air flow to classrooms",
        "Damper stuck",
    ],
    "BLR": [
        "Boiler lockout",
        "Low pressure",
        "Annual gas service",
        "Pilot light out",
        "Leak under boiler",
    ],
    "CAL": [
        "Water not hot",
        "Legionella temperature check",
        "Thermostat faulty",
        "Pressure valve dripping",
    ],
    "DB": [
        "Breaker tripping",
        "Thermal imaging survey",
        "Labelling missing",
        "Burning smell",
    ],
    "FAP": [
        "Panel showing fault",
        "Weekly fire alarm test",
        "Battery replacement",
        "Zone 3 false alarm",
    ],
    "MTR": ["Meter reading missing", "Meter display blank"],
    "PV": ["Inverter error code", "Panels need cleaning", "Low generation"],
    "LIFT": [
        "Lift stuck between floors",
        "Door not closing",
        "Six-monthly LOLER inspection",
    ],
}

# Room jobs (lights, doors...) also use messy room names
ROOM_NAMES = {
    "B1-101": ["Classroom 1", "Rm 101", "Class 1 Blk A"],
    "B1-102": ["Classroom 2", "Rm 102"],
    "B1-103": ["Main Hall", "Hall"],
    "B1-105": ["Classroom 3", "Rm 105 (1st floor)"],
    "B1-106": ["Classroom 4", "Rm 106"],
    "B1-107": ["IT Suite", "ICT room"],
    "B2-201": ["Science Lab", "Sci Lab", "Lab 1"],
    "B2-202": ["Library", "Lib"],
    "B2-204": ["Art Room", "Art"],
    "B2-205": ["Music Room", "Music"],
    "B3-301": ["Staff Room", "Staffroom"],
    "B3-302": ["Reception", "Front office"],
    "B3-304": ["Canteen", "Kitchen / Canteen"],
}
ROOM_PROBLEMS = [
    "Light flickering",
    "Door handle broken",
    "Window won't close",
    "Too cold",
    "Too hot",
    "Ceiling tile stained",
    "Socket not working",
    "Blind broken",
]

# Who usually fixes each kind of asset
CONTRACTORS = {
    "AHU": "ABC Mechanical Ltd",
    "BLR": "ABC Mechanical Ltd",
    "CAL": "AquaSafe Water Hygiene",
    "DB": "Sparks Electrical",
    "FAP": "SafeFire Services",
    "MTR": "Sparks Electrical",
    "PV": "Sparks Electrical",
    "LIFT": "LiftCare UK",
}
PRIORITIES = [
    "P1 - Emergency",
    "P2 - Urgent",
    "P3 - Routine",
    "P3 - Routine",
    "P4 - Planned",
]

# ---------------------------------------------------------------
# 2. MAKE THE JOBS
# ---------------------------------------------------------------
jobs = []
for number in range(1, 301):
    day = fake.date_between(
        start_date=pd.Timestamp("2026-03-01"), end_date=pd.Timestamp("2026-08-31")
    )
    raised = pd.Timestamp(day) + pd.Timedelta(
        minutes=random.randint(7 * 60, 17 * 60)
    )  # 7am to 5pm

    if random.random() < 0.65:  # 65% of jobs are about equipment
        tag = random.choice(list(ASSET_NAMES))
        asset_name = random.choice(ASSET_NAMES[tag])
        kind = "".join(ch for ch in tag.split("-")[0] if ch.isalpha())
        problem = random.choice(PROBLEMS[kind])
        location = ""
        contractor = random.choice([CONTRACTORS[kind], "In-house"])
    else:  # 35% are about a room
        tag = ""
        asset_name = ""
        room = random.choice(list(ROOM_NAMES))
        location = random.choice(ROOM_NAMES[room])
        problem = random.choice(ROOM_PROBLEMS)
        contractor = "In-house"

    status = random.choices(
        ["Completed", "Open", "On Hold", "Cancelled"], [80, 12, 5, 3]
    )[0]
    completed = (
        raised + pd.Timedelta(days=random.randint(0, 20))
        if status == "Completed"
        else None
    )

    jobs.append(
        {
            "Date Raised": raised,
            "Asset": asset_name,
            "Location": location,
            "Problem": problem,
            "Priority": random.choice(PRIORITIES),
            "Status": status,
            "Date Completed": completed,
            "Contractor": contractor,
            "Engineer": fake.name(),
            "Cost": round(random.uniform(40, 1500), 2)
            if status == "Completed"
            else None,
        }
    )

# Real story behind hidden fault 1: staff complain the Library is too hot
for day in ["2026-03-11 09:20", "2026-03-17 14:05", "2026-03-24 10:40"]:
    jobs.append(
        {
            "Date Raised": pd.Timestamp(day),
            "Asset": "",
            "Location": "Library",
            "Problem": "Too hot, radiators won't turn off",
            "Priority": "P2 - Urgent",
            "Status": "Completed" if day.startswith("2026-03-24") else "Cancelled",
            "Date Completed": pd.Timestamp("2026-03-27")
            if day.startswith("2026-03-24")
            else None,
            "Contractor": "ABC Mechanical Ltd",
            "Engineer": fake.name(),
            "Cost": 320.0 if day.startswith("2026-03-24") else None,
        }
    )

table = pd.DataFrame(jobs).sort_values("Date Raised").reset_index(drop=True)
table.insert(
    0, "WO Number", [f"WO-{26001 + i}" for i in range(len(table))]
)  # numbered in date order


# ---------------------------------------------------------------
# 3. MAKE IT MESSY (like a real export) AND SAVE
# ---------------------------------------------------------------
# Some dates typed in US style, some in UK style (the export tool is inconsistent)
def messy_date(value, row):
    if pd.isna(value):
        return ""
    return value.strftime("%m/%d/%Y %H:%M" if row % 9 == 0 else "%d/%m/%Y %H:%M")


for column in ["Date Raised", "Date Completed"]:
    table[column] = [messy_date(v, i) for i, v in enumerate(table[column])]

# Costs written with a pound sign sometimes
table["Cost"] = [
    ("£" + str(c)) if (pd.notna(c) and i % 4 == 0) else c
    for i, c in enumerate(table["Cost"])
]

# Extra spaces and random CAPITALS, because people type fast
table["Asset"] = [
    f"  {a.upper()} " if (a and i % 11 == 0) else a
    for i, a in enumerate(table["Asset"])
]

# 5 jobs were logged twice by mistake
table = pd.concat([table, table.sample(5, random_state=3)]).reset_index(drop=True)

table.to_csv("data/raw/cafm/work_orders.csv", index=False)
print(f"Saved data/raw/cafm/work_orders.csv with {len(table)} jobs")
