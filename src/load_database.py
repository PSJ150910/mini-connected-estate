"""ETL: Extract the raw data, Transform (clean it and swap messy names for official IDs),
Load it into one SQLite database.

Run with:  uv run python src/load_database.py
Creates:   data/twin.db   (deleted and rebuilt from raw data every time)
"""

import re
from pathlib import Path

import pandas as pd
from pypdf import PdfReader
from sqlmodel import Session, SQLModel, create_engine

from models import (
    Alias,
    Asset,
    Building,
    Document,
    DocumentLink,
    Reading,
    Room,
    Sensor,
    Site,
    WorkOrder,
)

DB_PATH = Path("data/twin.db")
DB_PATH.unlink(missing_ok=True)  # start fresh: the raw files are the truth
engine = create_engine(f"sqlite:///{DB_PATH}")
SQLModel.metadata.create_all(engine)  # make the empty tables from models.py

register = pd.read_csv("data/processed/register.csv", dtype=str).fillna("")
id_map = pd.read_csv("data/processed/id_map.csv", dtype=str).fillna("")
to_id = {(r.source, r.raw_name): r.matched_id for r in id_map.itertuples()}


def none_if_blank(value):
    return value if value else None


# ---------------------------------------------------------------
# 1. PLACES AND ASSETS (from the master register)
# ---------------------------------------------------------------
with Session(engine) as session:
    session.add(Site(id="GFA", name="Greenfield Academy"))
    for r in register.itertuples():
        if r.kind == "building":
            session.add(Building(id=r.id, name=r.name, site_id="GFA"))
        elif r.kind == "room":
            session.add(Room(id=r.id, name=r.name, building_id=r.building_id))
        else:
            session.add(
                Asset(
                    id=r.id,
                    name=r.name,
                    asset_type=r.asset_type,
                    room_id=r.room_id,
                    building_id=r.building_id,
                )
            )
    for r in id_map.itertuples():
        session.add(
            Alias(
                source=r.source,
                raw_name=r.raw_name,
                official_id=r.matched_id,
                confidence=int(r.confidence),
                method=r.method,
            )
        )
    session.commit()
print(f"Places: {len(register)} rows, aliases: {len(id_map)} rows")

# ---------------------------------------------------------------
# 2. BMS: sensors and readings
#    wide table (one column per sensor) -> long table (one row per reading)
# ---------------------------------------------------------------
ROOM_MEASURES = ("ZoneTemp", "CO2", "Occ")
all_readings = []
with Session(engine) as session:
    for path in sorted(Path("data/raw/bms").glob("*.csv")):
        table = pd.read_csv(path)
        # Block C writes day/month/year (13/03/2026). The others write 2026-03-13.
        uk_style = "/" in str(table["Timestamp"].iloc[0])
        date_format = "%d/%m/%Y %H:%M" if uk_style else "ISO8601"
        table["Timestamp"] = pd.to_datetime(table["Timestamp"], format=date_format)
        # The BMS clock does not jump in summer, so its times are UTC. Say so clearly.
        table["Timestamp"] = table["Timestamp"].dt.tz_localize("UTC")
        table = table.drop_duplicates()  # the BMS sent some rows twice

        for column in table.columns[1:]:
            if column.endswith("_kWh"):
                point, measure = column, "kWh"
            else:
                point, measure = column.rsplit("_", 1)
            official = to_id[("bms", point)]
            is_room = measure in ROOM_MEASURES
            session.add(
                Sensor(
                    id=column,
                    measure=measure,
                    room_id=official if is_room else None,
                    asset_id=None if is_room else official,
                )
            )

        long = table.melt(id_vars="Timestamp", var_name="sensor_id", value_name="value")
        long = long.dropna()  # missing readings: nothing to store
        long = long[long["value"] != -999]  # glitch values are not real readings
        all_readings.append(long.rename(columns={"Timestamp": "timestamp"}))
    session.commit()

readings = pd.concat(all_readings)
# For big tables, pandas loads much faster than adding rows one by one
readings.to_sql(
    Reading.__tablename__, engine, if_exists="append", index=False, chunksize=50_000
)
print(f"Readings: {len(readings):,} rows")


# ---------------------------------------------------------------
# 3. CAFM: work orders
# ---------------------------------------------------------------
def utc(timestamp):
    """pandas time -> normal Python time, marked as UTC (the database insists)."""
    return timestamp.tz_localize("UTC").to_pydatetime()


# The CAFM export covers 1 March to 31 August 2026 (jobs can finish up to 30 days later)
PERIOD_START, PERIOD_END = pd.Timestamp("2026-03-01"), pd.Timestamp("2026-09-30")


def read_both_ways(text):
    """'03/01/2026' could be 3 Jan (UK) or 1 Mar (US). Return both readings."""
    uk = pd.to_datetime(text, format="%d/%m/%Y %H:%M", errors="coerce")
    us = pd.to_datetime(text, format="%m/%d/%Y %H:%M", errors="coerce")
    return [d for d in dict.fromkeys([uk, us]) if pd.notna(d)]


def parse_raised(text):
    """Keep only readings inside the export period. If two remain, keep UK and warn."""
    options = [d for d in read_both_ways(text) if PERIOD_START <= d <= PERIOD_END]
    if not options:
        return None, "date not readable"
    return options[0], "day/month unclear" if len(options) > 1 else ""


def parse_completed(text, raised):
    """A job is finished on or after the day it was raised, so pick the closest such date."""
    if not text:
        return None, ""
    options = [d for d in read_both_ways(text) if raised is None or d >= raised]
    if not options:
        return None, "completed before raised"
    return min(options), ""


jobs = pd.read_csv("data/raw/cafm/work_orders.csv", dtype=str).fillna("")
jobs = jobs.drop_duplicates()  # 5 jobs were logged twice
with Session(engine) as session:
    for job in jobs.itertuples():
        raised, warn1 = parse_raised(job[2])
        completed, warn2 = parse_completed(job[8], raised)
        asset_name, location = job.Asset.strip(), job.Location.strip()
        cost = job.Cost.replace("£", "")
        session.add(
            WorkOrder(
                id=job[1],
                raised=utc(raised) if raised is not None else None,
                completed=utc(completed) if completed is not None else None,
                date_warning="; ".join(w for w in [warn1, warn2] if w),
                asset_id=none_if_blank(to_id.get(("cafm", asset_name), "")),
                room_id=none_if_blank(to_id.get(("cafm", location), "")),
                raw_asset_name=asset_name,
                raw_location=location,
                problem=job.Problem,
                priority=job.Priority,
                status=job.Status,
                contractor=job.Contractor,
                cost=float(cost) if cost else None,
            )
        )
    session.commit()
print(f"Work orders: {len(jobs)} rows")


# ---------------------------------------------------------------
# 4. DOCUMENTS: read the facts printed inside each PDF
# ---------------------------------------------------------------
def find(pattern, text):
    match = re.search(pattern, text)
    return match.group(1).strip() if match else ""


with Session(engine) as session:
    for path in sorted(Path("data/raw/docs").glob("*.pdf")):
        text = PdfReader(path).pages[0].extract_text()
        inspected = find(r"Date of inspection: (.+)", text)
        due = find(r"Next inspection due: (.+)", text)
        session.add(
            Document(
                id=path.name,
                doc_type=text.splitlines()[0].title(),
                area_text=find(r"Equipment / Area: (.+)", text),
                inspected=utc(pd.to_datetime(inspected)) if inspected else None,
                next_due=utc(pd.to_datetime(due)) if due else None,
            )
        )
        row = id_map[
            (id_map["source"] == "docs") & (id_map["raw_name"] == path.name)
        ].iloc[0]
        for entity in filter(None, row["matched_id"].split("|")):
            session.add(
                DocumentLink(
                    document_id=path.name, entity_id=entity, entity_kind=row["kind"]
                )
            )
    session.commit()
print(f"Documents: {len(list(Path('data/raw/docs').glob('*.pdf')))} rows")
print(f"Saved {DB_PATH}")
