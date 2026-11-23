"""Write the private answer key: the TRUE identity behind every messy name.

Run with:  uv run python src/make_answer_key.py
Creates:   data/answer_key/answer_key.csv

Module 2 must NOT read this file. We only use it at the end to mark our work.
"""

import csv
from pathlib import Path

# The BIM tag is the "true" ID. Every other column is what another system calls it.
# fmt: off
ASSETS = [
    # (BIM tag, BMS name, CAFM names, compliance documents)
    ("AHU-01", "B1_AHU1", "Air Handler 1 Blk A | AHU 1 Block A | air handling unit 1 - A", "O&M_AHU_1_2.pdf"),
    ("AHU-02", "B1_AHU2", "Air Handler 2 Blk A | AHU2 Blk A | Air handling unit no.2 (Block A)", "O&M_AHU_1_2.pdf"),
    ("AHU-03", "B2_AHU1", "Air Handler Blk B | AHU Science Block | B Block AHU", "AHU3_manual.pdf"),
    ("AHU-04", "B3_AHU1", "Air Handler Blk C | AHU - Admin | Admin block air handler", "AHU Admin O&M.pdf"),
    ("BLR-01", "", "Boiler 1 Blk A | Blk A boiler | Main Boiler (Teaching)", "Gas Safe - Boiler 1.pdf | Boiler_manual_Evomax.pdf"),
    ("BLR-02", "", "Boiler Blk B | Science block boiler | Boiler B", "GasSafety_ScienceBlk.pdf"),
    ("BLR-03", "", "Boiler Blk C | Admin Boiler | boiler - block c", "gas cert admin 2025.pdf"),
    ("CAL-01", "", "Calorifier Blk A | HW Cylinder A | Hot water tank Block A", "Legionella_RA_BlockA.pdf"),
    ("CAL-02", "", "Calorifier Blk C | HW Cylinder C | Kitchen hot water cylinder", "Legionella RA - Kitchen.pdf"),
    ("DB-01", "", "Main DB Blk A | Distribution Board A | DB1", "EICR_BlockA_2022.pdf"),
    ("DB-02", "", "DB Blk B | Distribution Board B | DB2 Science", "EICR DB2 final v2.pdf"),
    ("DB-03", "", "DB Blk C | Distribution Board C | DB3 Admin", "EICR_AdminBlock.pdf"),
    ("FAP-01", "", "Fire Panel Blk A | Fire alarm panel - Teaching | FA Panel A", "FireAlarm_Cert_TeachingBlock.pdf"),
    ("FAP-02", "", "Fire Panel Blk B | Fire alarm panel Library | FA Panel B", "FA cert Science Block Jan.pdf"),
    ("FAP-03", "", "Fire Panel Blk C | Fire alarm panel Reception | FA Panel C", "scan0043.pdf"),
    ("MTR-01", "MTR_BLKA_ELEC_kWh", "Elec Meter Blk A | Electricity meter A", ""),
    ("MTR-02", "MTR_BLKB_ELEC_kWh", "Elec Meter Blk B | Electricity meter B", ""),
    ("MTR-03", "MTR_BLKC_ELEC_kWh", "Elec Meter Blk C | Electricity meter C", ""),
    ("PV-01", "PV_ROOF_GEN_kWh", "Solar Panels | PV array roof C | Solar PV inverter", "Solar PV handover pack.pdf"),
    ("LIFT-01", "", "Lift | Passenger Lift Blk A | Main hall lift", "LOLER_Lift_Report.pdf | Lift_OM_Manual.pdf"),
]

ROOMS = [
    # (room ID, BMS prefix, CAFM names)
    ("B1-101", "BLKA_GF_CLS01", "Classroom 1 | Rm 101 | Class 1 Blk A"),
    ("B1-102", "BLKA_GF_CLS02", "Classroom 2 | Rm 102"),
    ("B1-103", "BLKA_GF_HALL", "Main Hall | Hall"),
    ("B1-104", "", ""),
    ("B1-105", "BLKA_1F_CLS03", "Classroom 3 | Rm 105 (1st floor)"),
    ("B1-106", "BLKA_1F_CLS04", "Classroom 4 | Rm 106"),
    ("B1-107", "BLKA_1F_ICT", "IT Suite | ICT room"),
    ("B2-201", "BLKB_GF_SCI_LAB", "Science Lab | Sci Lab | Lab 1"),
    ("B2-202", "BLKB_GF_LIBRARY", "Library | Lib"),
    ("B2-203", "BLKB_GF_PREP", ""),
    ("B2-204", "BLKB_1F_ART", "Art Room | Art"),
    ("B2-205", "BLKB_1F_MUSIC", "Music Room | Music"),
    ("B2-206", "", ""),
    ("B3-301", "Block C Staff Rm", "Staff Room | Staffroom"),
    ("B3-302", "Block C Reception", "Reception | Front office"),
    ("B3-303", "Block C Head Off", ""),
    ("B3-304", "Block C Canteen", "Canteen | Kitchen / Canteen"),
    ("B3-305", "", ""),
]

BUILDINGS = [
    # (building ID, BMS file, compliance documents)
    ("B1", "bms_export_block_a.csv", "Asbestos_Survey_Teaching.pdf | FRA_Teaching_Block.pdf"),
    ("B2", "bms_export_block_b.csv", "Asbestos survey Sci+Lib.pdf | Fire Risk Assessment - Science.pdf"),
    ("B3", "bms_export_block_c.csv", "ASB_AdminBlock_2026.pdf | FRA admin.pdf"),
]

HIDDEN_FAULTS = [
    ("FAULT-1", "B2-202", "Library heating valve stuck open 9-29 March 2026: room 5 C too hot day and night"),
    ("FAULT-2", "B2-201", "Science Lab CO2 sensor frozen at 612 ppm from 12 May 2026 10:00 onwards"),
]
# fmt: on

Path("data/answer_key").mkdir(exist_ok=True)
with open("data/answer_key/answer_key.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["kind", "true_id", "bms_name", "cafm_names", "documents"])
    for tag, bms, cafm, docs in ASSETS:
        writer.writerow(["asset", tag, bms, cafm, docs])
    for room_id, bms, cafm in ROOMS:
        writer.writerow(["room", room_id, bms, cafm, ""])
    for building_id, bms, docs in BUILDINGS:
        writer.writerow(["building", building_id, bms, "", docs])
    for fault_id, where, what in HIDDEN_FAULTS:
        writer.writerow(["fault", where, "", what, fault_id])

total = len(ASSETS) + len(ROOMS) + len(BUILDINGS) + len(HIDDEN_FAULTS)
print(f"Saved data/answer_key/answer_key.csv with {total} rows")
