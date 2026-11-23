"""Create compliance certificates and manuals as PDF files.

Run with:  uv run python src/make_documents.py
Creates:   about 24 PDFs in data/raw/docs/
"""

import random
from datetime import date, timedelta

from faker import Faker
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

random.seed(11)
Faker.seed(11)
fake = Faker("en_GB")

# ---------------------------------------------------------------
# 1. THE DOCUMENTS
#    (file name, document type, how the document names the asset,
#     BIM tag it really belongs to, date inspected, months valid)
#    File names are messy on purpose, like a real shared drive.
# ---------------------------------------------------------------
# Ruff, please don't reformat this table: keep one row per document
# fmt: off
DOCUMENTS = [
    # Fire alarm service certificates: valid 6 months
    ("FireAlarm_Cert_TeachingBlock.pdf", "Fire Alarm Service Certificate", "Fire Alarm Control Panel, Teaching Block", "FAP-01", date(2026, 6, 2), 6),
    ("FA cert Science Block Jan.pdf", "Fire Alarm Service Certificate", "FACP - Science & Library Building", "FAP-02", date(2026, 1, 14), 6),
    ("scan0043.pdf", "Fire Alarm Service Certificate", "Admin Block fire panel", "FAP-03", date(2026, 9, 8), 6),
    # Electrical installation condition reports (EICR): valid 5 years
    ("EICR_BlockA_2022.pdf", "Electrical Installation Condition Report", "Main Distribution Board MDB-A", "DB-01", date(2022, 4, 20), 60),
    ("EICR DB2 final v2.pdf", "Electrical Installation Condition Report", "Sub-main DB Science", "DB-02", date(2021, 8, 3), 60),
    ("EICR_AdminBlock.pdf", "Electrical Installation Condition Report", "Distribution Board, Admin", "DB-03", date(2025, 2, 11), 60),
    # Gas safety certificates: valid 12 months
    ("Gas Safe - Boiler 1.pdf", "Gas Safety Certificate", "Boiler No.1 (Ideal Evomax 150)", "BLR-01", date(2025, 10, 1), 12),
    ("GasSafety_ScienceBlk.pdf", "Gas Safety Certificate", "Science Block Boiler", "BLR-02", date(2026, 3, 19), 12),
    ("gas cert admin 2025.pdf", "Gas Safety Certificate", "Boiler - Admin Plant Rm", "BLR-03", date(2025, 7, 22), 12),
    # Legionella risk assessments: valid 24 months
    ("Legionella_RA_BlockA.pdf", "Legionella Risk Assessment", "HWS Calorifier CAL1", "CAL-01", date(2024, 5, 9), 24),
    ("Legionella RA - Kitchen.pdf", "Legionella Risk Assessment", "Kitchen HW Calorifier", "CAL-02", date(2025, 11, 30), 24),
    # Lift thorough examination (LOLER): valid 6 months
    ("LOLER_Lift_Report.pdf", "LOLER Thorough Examination Report", "Passenger Lift L1", "LIFT-01", date(2026, 4, 15), 6),
    # Asbestos surveys (whole building): valid 12 months
    ("Asbestos_Survey_Teaching.pdf", "Asbestos Management Survey", "Teaching Block (whole building)", "B1", date(2026, 2, 3), 12),
    ("Asbestos survey Sci+Lib.pdf", "Asbestos Management Survey", "Science and Library Block", "B2", date(2025, 9, 27), 12),
    ("ASB_AdminBlock_2026.pdf", "Asbestos Management Survey", "Admin & Staff Block", "B3", date(2026, 5, 12), 12),
    # Operation and maintenance manuals: never expire (months = 0)
    ("O&M_AHU_1_2.pdf", "O&M Manual", "Air Handling Units AHU/A/01 & AHU/A/02", "AHU-01", date(2019, 8, 1), 0),
    ("AHU3_manual.pdf", "O&M Manual", "AHU Science Block (Daikin D-AHU)", "AHU-03", date(2019, 8, 1), 0),
    ("AHU Admin O&M.pdf", "O&M Manual", "Admin AHU", "AHU-04", date(2020, 1, 15), 0),
    ("Boiler_manual_Evomax.pdf", "O&M Manual", "Ideal Evomax 150 boilers (all blocks)", "BLR-01", date(2019, 8, 1), 0),
    ("Solar PV handover pack.pdf", "O&M Manual", "Roof PV array 30kWp + SMA inverter", "PV-01", date(2023, 6, 30), 0),
    ("Lift_OM_Manual.pdf", "O&M Manual", "Passenger lift L1 (Stannah)", "LIFT-01", date(2019, 8, 1), 0),
    # Fire risk assessments for each building: valid 12 months
    ("FRA_Teaching_Block.pdf", "Fire Risk Assessment", "Teaching Block", "B1", date(2025, 11, 1), 12),
    ("Fire Risk Assessment - Science.pdf", "Fire Risk Assessment", "Science & Library", "B2", date(2026, 7, 6), 12),
    ("FRA admin.pdf", "Fire Risk Assessment", "Admin Block", "B3", date(2024, 10, 10), 12),
]
# fmt: on


def add_months(start, months):
    """Return the date a number of months after start (roughly)."""
    return start + timedelta(days=round(months * 30.44))


def write_pdf(file_name, doc_type, asset_text, inspected, months):
    """Draw one simple certificate page and save it as a PDF."""
    pdf = canvas.Canvas(f"data/raw/docs/{file_name}", pagesize=A4)
    width, height = A4
    company = fake.company()

    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(50, height - 70, doc_type.upper())
    pdf.setFont("Helvetica", 11)
    pdf.drawString(50, height - 95, f"Issued by: {company}")
    pdf.line(50, height - 105, width - 50, height - 105)

    lines = [
        f"Certificate No: {fake.bothify('??-#####').upper()}",
        "Site: Greenfield Academy, 12 School Lane",
        f"Equipment / Area: {asset_text}",
        f"Date of inspection: {inspected.strftime('%d %B %Y')}",
    ]
    if months:
        lines.append(
            f"Next inspection due: {add_months(inspected, months).strftime('%d %B %Y')}"
        )
        lines.append(
            f"Result: {random.choice(['Satisfactory', 'Satisfactory', 'Satisfactory with observations'])}"
        )
    else:
        lines.append(
            f"Manufacturer documentation, handover date {inspected.strftime('%B %Y')}"
        )
    lines.append(f"Engineer: {fake.name()}")

    y = height - 140
    for line in lines:
        pdf.drawString(50, y, line)
        y -= 22

    pdf.setFont("Helvetica-Oblique", 9)
    pdf.drawString(
        50,
        60,
        "Sample document generated for the Mini Connected Estate learning project.",
    )
    pdf.save()


TODAY = date(2026, 11, 23)
expired = 0
for file_name, doc_type, asset_text, tag, inspected, months in DOCUMENTS:
    write_pdf(file_name, doc_type, asset_text, inspected, months)
    if months and add_months(inspected, months) < TODAY:
        expired += 1

print(f"Saved {len(DOCUMENTS)} PDFs in data/raw/docs/ ({expired} are already expired)")
