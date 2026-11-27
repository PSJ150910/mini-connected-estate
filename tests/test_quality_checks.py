"""Tests for the data trust checker. Run with:  uv run python -m pytest

Each test builds a TINY fake table where we already know the right answer,
runs one check on it, and asserts (insists) that the check gives that answer.
If someone breaks a check later, a test goes red and tells us at once.
"""

from datetime import UTC, datetime

import pandas as pd
import pytest
from sqlalchemy import create_engine, text

import audit
from quality_checks import (
    check_certificates,
    check_duplicate_assets,
    check_duplicate_jobs,
    check_flat_sensors,
    check_night_cooling,
    check_reading_ranges,
    check_sensor_silence,
    check_work_orders_valid,
)
from quality_report import score_table


def fake_readings(values, sensor="ROOM1_CO2", measure="CO2", start="2026-05-01"):
    """One reading every 15 minutes for one sensor in building B1."""
    times = pd.date_range(start, periods=len(values), freq="15min", tz="UTC")
    return pd.DataFrame(
        {"sensor_id": sensor, "building_id": "B1", "measure": measure,
         "timestamp": times, "value": values}
    )  # fmt: skip


def fake_jobs(**changes):
    """Two good work orders. Pass changes to break one of them on purpose."""
    jobs = pd.DataFrame(
        {
            "id": ["WO-26001", "WO-26002"],
            "building_id": "B1",
            "asset_id": ["AHU-01", "BLR-01"],
            "room_id": None,
            "problem": ["Noisy fan", "No heating"],
            "priority": "P3 - Routine",
            "status": "Completed",
            "cost": [100.0, 200.0],
            "date_warning": "",
            "raised": pd.to_datetime(["2026-03-01", "2026-03-02"], utc=True),
            "completed": pd.to_datetime(["2026-03-03", "2026-03-04"], utc=True),
        }
    )
    for column, value in changes.items():
        jobs.loc[1, column] = value
    return jobs


# ---------- timely ----------
def test_frozen_sensor_is_caught():
    values = [600 + i % 7 for i in range(40)] + [612.0] * 40  # 10 hours stuck
    found = check_flat_sensors(fake_readings(values))
    assert not found["passed"].iloc[0]
    assert "stuck at 612.0" in found["detail"].iloc[0]


def test_moving_sensor_passes():
    values = [600 + i % 7 for i in range(80)]
    assert check_flat_sensors(fake_readings(values))["passed"].all()


def test_silent_sensor_is_caught():
    readings = fake_readings([20.0] * 20)
    readings = readings.drop(index=range(5, 15))  # 10 readings missing = 2.75 hours
    found = check_sensor_silence(readings)
    assert not found["passed"].iloc[0]


def test_expired_certificate_is_caught():
    docs = pd.DataFrame(
        {
            "id": ["old.pdf", "new.pdf"],
            "entity_id": ["BLR-01", "BLR-02"],
            "building_id": ["B1", "B2"],
            "next_due": pd.to_datetime(["2026-01-01", "2027-01-01"], utc=True),
        }
    )
    found = check_certificates(docs, today=datetime(2026, 6, 1, tzinfo=UTC))
    assert found["passed"].tolist() == [False, True]


# ---------- valid ----------
def test_impossible_reading_is_caught():
    found = check_reading_ranges(fake_readings([21.0, 22.0, -999.0], measure="ZoneTemp"))
    assert not found["passed"].iloc[0]
    assert found["detail"].iloc[0] == "1 impossible readings"


def test_good_work_orders_pass():
    assert check_work_orders_valid(fake_jobs())["passed"].all()


def test_unclear_date_is_caught():
    found = check_work_orders_valid(fake_jobs(date_warning="day/month unclear"))
    assert found["passed"].tolist() == [True, False]
    assert "date is unclear" in found["detail"].iloc[1]


def test_job_finished_before_it_started_is_caught():
    found = check_work_orders_valid(
        fake_jobs(completed=pd.Timestamp("2026-02-01", tz="UTC"))
    )
    assert found["passed"].tolist() == [True, False]


def test_wrong_priority_is_caught():
    found = check_work_orders_valid(fake_jobs(priority="Very urgent!!"))
    assert found["passed"].tolist() == [True, False]


# ---------- unique ----------
def test_duplicate_asset_is_caught():
    assets = pd.DataFrame(
        {
            "id": ["AHU-01", "AHU-09", "BLR-01"],
            "asset_type": ["AHU", "AHU", "BLR"],
            "name": ["Air handler", "Air handler", "Boiler"],
            "room_id": ["B1-104", "B1-104", "B1-104"],
            "building_id": "B1",
        }
    )
    assert check_duplicate_assets(assets)["passed"].tolist() == [False, False, True]


def test_same_job_twice_is_caught():
    jobs = fake_jobs(
        asset_id="AHU-01", problem="Noisy fan", raised=pd.Timestamp("2026-03-01 15:00", tz="UTC")
    )
    found = check_duplicate_jobs(jobs).set_index("item")
    assert not found.loc["WO-26002", "passed"]


# ---------- consistent ----------
def test_room_warm_every_night_is_caught():
    hours = 24 * 4 * 6  # six days of readings
    readings = fake_readings([22.0] * hours, sensor="LIB_ZoneTemp", measure="ZoneTemp")
    found = check_night_cooling(readings)
    assert not found["passed"].iloc[0]


# ---------- score ----------
def test_score_is_average_of_checks():
    results = pd.DataFrame(
        {
            "building_id": "B1",
            "check_id": ["A", "A", "A", "A", "B"],
            "dimension": "valid",
            "rule": "x",
            "passed": [True, True, True, False, True],
        }
    )
    per_check, per_building = score_table(results)
    assert per_check["score"].tolist() == [75.0, 100.0]
    assert per_building["B1"] == 87.5  # (75 + 100) / 2, not 4 out of 5


# ---------- audit log ----------
def test_audit_log_records_who_and_blocks_deleting(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE asset (id TEXT PRIMARY KEY, name TEXT, "
                          "asset_type TEXT, room_id TEXT, building_id TEXT)"))  # fmt: skip
    audit.install(engine, tables={"asset": audit.WATCHED["asset"]})
    with engine.begin() as conn:
        conn.execute(text("UPDATE app_user SET name = 'Tester', reason = 'test'"))
        conn.execute(text("INSERT INTO asset VALUES ('AHU-01', 'Old', 'AHU', 'R1', 'B1')"))
        conn.execute(text("UPDATE asset SET name = 'New' WHERE id = 'AHU-01'"))
    with engine.connect() as conn:
        log = conn.execute(text("SELECT changed_by, action FROM audit_log")).all()
    assert log == [("Tester", "INSERT"), ("Tester", "UPDATE")]

    with pytest.raises(Exception, match="append-only"):  # this MUST fail
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM audit_log"))
