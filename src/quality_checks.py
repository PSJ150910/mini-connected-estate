"""The DATA TRUST CHECKER: every rule from docs/data_rules.md, written as code.

Each check returns a small table with ONE ROW PER THING CHECKED:
    building_id | item | passed (True/False) | detail
So one check can say "15 sensors checked in B2, 14 passed, 1 failed, and here is why".
The score (in quality_report.py) is then just "how many rows passed".

This file only READS data. It never changes the database.
"""

from datetime import UTC, datetime

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


# ---------------------------------------------------------------
# 3. UNIQUE: no duplicates
# ---------------------------------------------------------------
def check_duplicate_assets(assets):
    """UNIQ-01: no two assets with the same type and name in the same room."""
    key = ["asset_type", "name", "room_id"]
    is_copy = assets.duplicated(subset=key, keep=False)  # keep=False marks BOTH copies
    return result(
        assets["building_id"],
        assets["id"],
        ~is_copy,
        is_copy.map({True: "same type, name and room as another asset", False: ""}),
    )


def check_duplicate_jobs(work_orders):
    """UNIQ-02: the same problem on the same thing is not logged twice within 1 day."""
    jobs = work_orders.copy()
    jobs["thing"] = jobs["asset_id"].fillna(jobs["room_id"])
    jobs = jobs.sort_values(["thing", "problem", "raised"])
    gap = jobs.groupby(["thing", "problem"])["raised"].diff()  # time since the last one
    is_repeat = gap <= pd.Timedelta(days=1)
    return result(
        jobs["building_id"],
        jobs["id"],
        ~is_repeat,
        is_repeat.map({True: "same problem raised again within 1 day", False: ""}),
    )


# ---------------------------------------------------------------
# 5. TIMELY: data is still arriving, papers are in date
# ---------------------------------------------------------------
def silent_periods(readings):
    """Every gap between two readings of the same sensor that is longer than 2 hours."""
    readings = readings.sort_values(["sensor_id", "timestamp"])
    gap = readings.groupby("sensor_id")["timestamp"].diff()
    found = readings[gap > MAX_SILENCE].assign(
        silent_from=readings["timestamp"] - gap, hours=gap.dt.total_seconds() / 3600
    )
    return found[["sensor_id", "building_id", "silent_from", "timestamp", "hours"]]


def check_sensor_silence(readings):
    """TIME-01: no sensor is silent for more than 2 hours (inside the export period)."""
    gaps = silent_periods(readings)
    worst = gaps.groupby("sensor_id")["hours"].max()
    sensors = readings[["sensor_id", "building_id"]].drop_duplicates()
    hours = sensors["sensor_id"].map(worst)
    detail = [
        f"silent for {h:.1f} hours" if pd.notna(h) else "" for h in hours
    ]
    return result(sensors["building_id"], sensors["sensor_id"], hours.isna(), detail)


def flat_periods(readings):
    """Every run of the SAME value lasting longer than 6 hours (a frozen sensor)."""
    readings = readings[readings["measure"].isin(FLAT_MEASURES)]
    readings = readings.sort_values(["sensor_id", "timestamp"])
    # A new 'run' starts whenever the value changes (or the sensor changes)
    changed = (readings["value"] != readings.groupby("sensor_id")["value"].shift())
    readings = readings.assign(run=changed.cumsum())
    runs = readings.groupby(["sensor_id", "building_id", "run"]).agg(
        value=("value", "first"),
        start=("timestamp", "min"),
        end=("timestamp", "max"),
        n=("value", "size"),
    )
    runs["hours"] = runs["n"] * EXPECTED_STEP.total_seconds() / 3600
    long_runs = runs[runs["hours"] > MAX_FLAT.total_seconds() / 3600]
    return long_runs.reset_index().drop(columns="run")


def check_flat_sensors(readings):
    """TIME-02: no temperature or CO2 sensor shows the same value for over 6 hours."""
    flat = flat_periods(readings)
    sensors = readings.loc[
        readings["measure"].isin(FLAT_MEASURES), ["sensor_id", "building_id"]
    ].drop_duplicates()
    first = flat.groupby("sensor_id").first()
    detail = [
        f"stuck at {first.at[s, 'value']} from {first.at[s, 'start']:%d %b %H:%M} "
        f"for {first.at[s, 'hours']:.0f} hours"
        if s in first.index
        else ""
        for s in sensors["sensor_id"]
    ]
    return result(
        sensors["building_id"],
        sensors["sensor_id"],
        ~sensors["sensor_id"].isin(flat["sensor_id"]),
        detail,
    )


def check_certificates(documents, today=None):
    """TIME-03: no certificate is past its 'next inspection due' date.
    Manuals have no due date, so they are not checked."""
    today = today or datetime.now(UTC)
    certs = documents[documents["next_due"].notna()]
    expired = certs["next_due"] < pd.Timestamp(today)
    detail = [
        f"expired on {d:%d %b %Y}" if e else f"valid until {d:%d %b %Y}"
        for d, e in zip(certs["next_due"], expired)
    ]
    return result(
        certs["building_id"], certs["id"] + " (" + certs["entity_id"] + ")", ~expired, detail
    )


# ---------------------------------------------------------------
# 6. CONSISTENT: the data agrees with itself and with other sources
# ---------------------------------------------------------------
def check_night_cooling(readings):
    """CONS-01: room temperature agrees with the heating timetable.
    The heating is off at night, so the 1am-5am average should be below 20 C."""
    temps = readings[readings["measure"] == "ZoneTemp"]
    night = temps[temps["timestamp"].dt.hour.between(1, 4)]
    per_night = night.groupby(
        ["sensor_id", "building_id", night["timestamp"].dt.date]
    )["value"].mean()
    hot = per_night[per_night > NIGHT_MAX_TEMP].reset_index()
    hot_count = hot.groupby("sensor_id").size()
    first_hot = hot.groupby("sensor_id")["timestamp"].min()
    sensors = temps[["sensor_id", "building_id"]].drop_duplicates()
    counts = sensors["sensor_id"].map(hot_count).fillna(0).astype(int)
    detail = [
        f"{c} warm nights, first on {first_hot[s]:%d %b}" if c else ""
        for s, c in zip(sensors["sensor_id"], counts)
    ]
    return result(
        sensors["building_id"], sensors["sensor_id"], counts <= MAX_HOT_NIGHTS, detail
    )


def check_assets_have_certificates(assets, documents):
    """CONS-02: every asset the law cares about (boiler, lift ...) has a document."""
    must = assets[assets["asset_type"].isin(NEEDS_CERTIFICATE)]
    has_doc = must["id"].isin(documents["entity_id"])
    return result(
        must["building_id"],
        must["id"],
        has_doc,
        has_doc.map({True: "", False: "no certificate found"}),
    )


# ---------------------------------------------------------------
# 7. THE LIST OF ALL CHECKS (the report runs every one of these)
# ---------------------------------------------------------------
CHECKS = [
    # (id, dimension, rule in plain English, function that needs the data)
    ("COMP-01", "complete", "Every sensor sends at least 98% of its readings",
     lambda d: check_sensor_completeness(d["readings"])),
    ("COMP-02", "complete", "Every completed job has a finish date and a cost",
     lambda d: check_completed_jobs(d["work_orders"])),
    ("UNIQ-01", "unique", "No asset is listed twice",
     lambda d: check_duplicate_assets(d["assets"])),
    ("UNIQ-02", "unique", "No job is logged twice within 1 day",
     lambda d: check_duplicate_jobs(d["work_orders"])),
    ("VALID-01", "valid", "Every reading is physically possible",
     lambda d: check_reading_ranges(d["readings"])),
    ("VALID-02", "valid", "Every job has a proper ID, priority, status, cost and clear dates",
     lambda d: check_work_orders_valid(d["work_orders"])),
    ("TIME-01", "timely", "No sensor is silent for more than 2 hours",
     lambda d: check_sensor_silence(d["readings"])),
    ("TIME-02", "timely", "No temperature or CO2 sensor is stuck for over 6 hours",
     lambda d: check_flat_sensors(d["readings"])),
    ("TIME-03", "timely", "No certificate is past its expiry date",
     lambda d: check_certificates(d["documents"])),
    ("CONS-01", "consistent", "Rooms cool below 20 C at night when the heating is off",
     lambda d: check_night_cooling(d["readings"])),
    ("CONS-02", "consistent", "Every boiler, calorifier, board, fire panel and lift has a certificate",
     lambda d: check_assets_have_certificates(d["assets"], d["documents"])),
]  # fmt: skip


def run_all_checks(data):
    """Run every check and stack the answers into one big table."""
    tables = []
    for check_id, dimension, rule, function in CHECKS:
        found = function(data)
        tables.append(found.assign(check_id=check_id, dimension=dimension, rule=rule))
    return pd.concat(tables, ignore_index=True)
