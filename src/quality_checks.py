"""The DATA TRUST CHECKER: every rule from docs/data_rules.md, written as code.

Each check returns a small table with ONE ROW PER THING CHECKED:
    building_id | item | passed (True/False) | detail
So one check can say "15 sensors checked in B2, 14 passed, 1 failed, and here is why".
The score (in quality_report.py) is then just "how many rows passed".

This file only READS data. It never changes the database.
"""

import pandas as pd
import pandera.pandas as pa
from sqlalchemy import text

# Rules that people agreed on. Change a number here, not inside the code below.
EXPECTED_STEP = pd.Timedelta(minutes=15)  # the BMS sends one reading every 15 minutes
MIN_COMPLETE = 0.98  # a sensor must deliver at least 98% of its readings
MAX_SILENCE = pd.Timedelta(hours=2)  # no sensor silent for more than 2 hours
MAX_FLAT = pd.Timedelta(hours=6)  # a real room never shows the same number for 6 hours
FLAT_MEASURES = ["ZoneTemp", "CO2"]  # only measures that should always move a little
NIGHT_MAX_TEMP = 20.0  # heating is off at night: rooms should cool below 20 C
MAX_HOT_NIGHTS = 3  # one or two warm nights can happen, more is a problem
NEEDS_CERTIFICATE = ["BLR", "CAL", "DB", "FAP", "LIFT"]  # the law wants papers for these

# What a physically possible reading looks like, for each kind of sensor
READING_LIMITS = {
    "ZoneTemp": (5, 40),  # deg C inside a school room
    "CO2": (350, 5000),  # ppm; outdoor air is about 420
    "Occ": (0, 200),  # people; our biggest room holds 120
    "SAT": (-15, 45),  # supply air, deg C: when the fan is off it shows OUTDOOR air
    "FanStatus": (0, 1),  # off or on
    "kWh": (0, 100),  # energy in 15 minutes
}


# ---------------------------------------------------------------
# 1. LOAD: read the tables we need from the database, once
# ---------------------------------------------------------------
def load_data(engine):
    """Read the database into pandas tables, each with a building_id column."""
    with engine.connect() as conn:

        def sql(query):
            return pd.read_sql(text(query), conn)

        data = {
            "assets": sql("SELECT * FROM asset"),
            "sensors": sql(
                """SELECT s.id AS sensor_id, s.measure,
                          COALESCE(r.building_id, a.building_id) AS building_id
                   FROM sensor s
                   LEFT JOIN room r ON r.id = s.room_id
                   LEFT JOIN asset a ON a.id = s.asset_id"""
            ),
            "readings": sql("SELECT sensor_id, timestamp, value FROM reading"),
            "work_orders": sql(
                """SELECT w.*, COALESCE(a.building_id, r.building_id) AS building_id
                   FROM workorder w
                   LEFT JOIN asset a ON a.id = w.asset_id
                   LEFT JOIN room r ON r.id = w.room_id"""
            ),
            "documents": sql(
                """SELECT d.*, l.entity_id,
                          CASE WHEN l.entity_kind = 'building' THEN l.entity_id
                               ELSE a.building_id END AS building_id
                   FROM document d
                   JOIN documentlink l ON l.document_id = d.id
                   LEFT JOIN asset a ON a.id = l.entity_id"""
            ),
        }
    # SQLite gives times back as text, PostgreSQL as real times: make both the same
    data["readings"]["timestamp"] = pd.to_datetime(data["readings"]["timestamp"], utc=True)
    for column in ["raised", "completed"]:
        data["work_orders"][column] = pd.to_datetime(data["work_orders"][column], utc=True)
    data["documents"]["next_due"] = pd.to_datetime(data["documents"]["next_due"], utc=True)
    # Put the building and measure next to every reading (a JOIN, done in pandas)
    data["readings"] = data["readings"].merge(data["sensors"], on="sensor_id")
    return data


def result(building_id, item, passed, detail=""):
    """Build the standard 'one row per thing checked' table."""
    return pd.DataFrame(
        {"building_id": building_id, "item": item, "passed": passed, "detail": detail}
    )


# ---------------------------------------------------------------
# 2. COMPLETE: nothing missing
# ---------------------------------------------------------------
def check_sensor_completeness(readings):
    """COMP-01: every sensor delivers at least 98% of the readings it should."""
    start, end = readings["timestamp"].min(), readings["timestamp"].max()
    expected = (end - start) / EXPECTED_STEP + 1  # how many 15-minute slots exist
    per_sensor = readings.groupby(["sensor_id", "building_id"]).size().reset_index(name="n")
    share = per_sensor["n"] / expected
    return result(
        per_sensor["building_id"],
        per_sensor["sensor_id"],
        share >= MIN_COMPLETE,
        "has " + (share * 100).round(1).astype(str) + "% of its readings",
    )


# Pandera: describe what a GOOD work order looks like, column by column
completed_job_schema = pa.DataFrameSchema(
    {
        "completed": pa.Column(nullable=False),  # a finished job has a finish date
        "cost": pa.Column(float, pa.Check.gt(0, error="cost must be above 0"), nullable=False),
    }
)


def failed_rows(schema, table):
    """Run a Pandera schema and return {row number: what went wrong}.
    lazy=True means 'find ALL problems', not just stop at the first one."""
    try:
        schema.validate(table, lazy=True)
        return {}
    except pa.errors.SchemaErrors as errors:
        problems = {}
        for case in errors.failure_cases.itertuples():
            if pd.notna(case.index):
                where = case.column if isinstance(case.column, str) else "row"
                problems.setdefault(int(case.index), []).append(f"{where}: {case.check}")
        return {row: "; ".join(why) for row, why in problems.items()}


def check_completed_jobs(work_orders):
    """COMP-02: every completed job has a completed date and a cost."""
    done = work_orders[work_orders["status"] == "Completed"]
    problems = failed_rows(completed_job_schema, done)
    return result(
        done["building_id"],
        done["id"],
        [row not in problems for row in done.index],
        [problems.get(row, "") for row in done.index],
    )


# ---------------------------------------------------------------
# 4. VALID: values make sense
# ---------------------------------------------------------------
def check_reading_ranges(readings):
    """VALID-01: every reading is physically possible for its kind of sensor.
    One row per sensor: it passes if ALL its readings are inside the limits."""
    low = readings["measure"].map(lambda m: READING_LIMITS[m][0])
    high = readings["measure"].map(lambda m: READING_LIMITS[m][1])
    readings = readings.assign(bad=~readings["value"].between(low, high))
    per_sensor = readings.groupby(["sensor_id", "building_id"])["bad"].sum().reset_index()
    return result(
        per_sensor["building_id"],
        per_sensor["sensor_id"],
        per_sensor["bad"] == 0,
        per_sensor["bad"].astype(str) + " impossible readings",
    )


work_order_schema = pa.DataFrameSchema(
    {
        "id": pa.Column(str, pa.Check.str_matches(r"^WO-\d{5}$"), unique=True),
        "priority": pa.Column(
            str,
            pa.Check.isin(["P1 - Emergency", "P2 - Urgent", "P3 - Routine", "P4 - Planned"]),
        ),
        "status": pa.Column(str, pa.Check.isin(["Open", "On Hold", "Completed", "Cancelled"])),
        "cost": pa.Column(float, pa.Check.in_range(0, 50_000), nullable=True),
        "raised": pa.Column(nullable=False),
        "date_warning": pa.Column(str, pa.Check.eq("", error="date is unclear")),
    },
    # A check on the whole row: a job cannot finish before it starts
    checks=pa.Check(
        lambda df: df["completed"].isna() | (df["completed"] >= df["raised"]),
        error="completed before raised",
    ),
)


def check_work_orders_valid(work_orders):
    """VALID-02: every work order has a proper ID, priority, status, cost and clear dates."""
    problems = failed_rows(work_order_schema, work_orders)
    return result(
        work_orders["building_id"],
        work_orders["id"],
        [row not in problems for row in work_orders.index],
        [problems.get(row, "") for row in work_orders.index],
    )
