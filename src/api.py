"""The digital twin API: a "menu" of web addresses that other programs can call.

Run with:   uv run python -m uvicorn api:app --app-dir src --reload
Then open:  http://127.0.0.1:8000/docs   (FastAPI builds this page for you)

By default it reads data/twin.db (SQLite). To use PostgreSQL in Docker instead:
    $env:DATABASE_URL = "postgresql+pg8000://twin:twin_local_only@localhost:5432/twin"
"""

import os
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import text
from sqlmodel import Session, create_engine, desc, select

from models import (
    Alias,
    Asset,
    Building,
    Document,
    DocumentLink,
    Reading,
    Room,
    Sensor,
    WorkOrder,
)

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///data/twin.db")
engine = create_engine(DATABASE_URL)

app = FastAPI(
    title="Mini Connected Estate API",
    description="One ID for every asset, joining BIM, BMS, CAFM and documents.",
)


def get_session():
    """FastAPI calls this for every request: open a database session, then close it."""
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]  # "this endpoint needs a session"


def as_utc(moment):
    """Times typed without a time zone (2026-03-01) are read as UTC, like our data."""
    return moment.replace(tzinfo=UTC) if moment.tzinfo is None else moment


def asset_or_404(session, asset_id):
    asset = session.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail=f"No asset called {asset_id}")
    return asset


# ---------------------------------------------------------------
# THE MENU: each @app.get(...) is one web address
# ---------------------------------------------------------------
@app.get("/buildings")
def list_buildings(session: SessionDep):
    """All buildings on the campus."""
    return session.exec(select(Building)).all()


@app.get("/rooms/{room_id}")
def get_room(room_id: str, session: SessionDep):
    """One room, with its assets and sensors."""
    room = session.get(Room, room_id)
    if room is None:
        raise HTTPException(status_code=404, detail=f"No room called {room_id}")
    return {
        "room": room,
        "assets": session.exec(select(Asset).where(Asset.room_id == room_id)).all(),
        "sensors": session.exec(select(Sensor).where(Sensor.room_id == room_id)).all(),
    }


@app.get("/assets/{asset_id}")
def get_asset(asset_id: str, session: SessionDep):
    """EVERYTHING about one asset, from all four systems, in one answer."""
    asset = asset_or_404(session, asset_id)
    sensors = session.exec(select(Sensor).where(Sensor.asset_id == asset_id)).all()
    latest = {}
    for sensor in sensors:  # the newest reading of each sensor
        reading = session.exec(
            select(Reading)
            .where(Reading.sensor_id == sensor.id)
            .order_by(desc(Reading.timestamp))
        ).first()
        latest[sensor.id] = reading
    return {
        "asset": asset,  # from BIM
        "latest_readings": latest,  # from BMS
        "work_orders": get_work_orders(asset_id, session),  # from CAFM
        "documents": session.exec(  # from the PDFs
            select(Document)
            .join(DocumentLink)
            .where(DocumentLink.entity_id == asset_id)
        ).all(),
        "also_known_as": [  # every messy name that means this asset
            {"source": alias.source, "name": alias.raw_name}
            for alias in session.exec(
                select(Alias).where(Alias.official_id.contains(asset_id))
            )
        ],
    }


@app.get("/assets/{asset_id}/readings")
def get_readings(
    asset_id: str,
    session: SessionDep,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = 100,
):
    """Sensor readings for one asset, newest first. Optional time window."""
    asset_or_404(session, asset_id)
    query = (
        select(Reading)
        .join(Sensor)
        .where(Sensor.asset_id == asset_id)
        .order_by(desc(Reading.timestamp))
        .limit(limit)
    )
    if start:
        query = query.where(Reading.timestamp >= as_utc(start))
    if end:
        query = query.where(Reading.timestamp < as_utc(end))
    return session.exec(query).all()


@app.get("/assets/{asset_id}/work-orders")
def get_work_orders(asset_id: str, session: SessionDep):
    """Repair jobs for one asset, newest first."""
    asset_or_404(session, asset_id)
    query = (
        select(WorkOrder)
        .where(WorkOrder.asset_id == asset_id)
        .order_by(desc(WorkOrder.raised))
    )
    return session.exec(query).all()


@app.get("/resolve")
def resolve_name(name: str, session: SessionDep):
    """Type any messy name (e.g. 'AHU2 Blk A') and get the official ID back."""
    matches = session.exec(
        select(Alias).where(Alias.raw_name.ilike(name.strip()))
    ).all()
    if not matches:
        raise HTTPException(status_code=404, detail=f"Never seen the name '{name}'")
    return matches


# ---------------------------------------------------------------
# MODULE 3: data trust (quality report and audit log)
# ---------------------------------------------------------------
def rows(session, query, **params):
    """Run plain SQL and return a list of dictionaries (FastAPI turns them into JSON)."""
    result = session.connection().execute(text(query), params)
    return [dict(row._mapping) for row in result]


@app.get("/quality")
def quality_overview(session: SessionDep):
    """Data quality score (0-100) for every building, from the last quality_report.py run."""
    scores = rows(session, "SELECT * FROM quality_score ORDER BY building_id, check_id")
    buildings = {}
    for row in scores:
        buildings.setdefault(row["building_id"], []).append(row["score"])
    return {
        "checked_at": scores[0]["checked_at"] if scores else None,
        "buildings": {b: round(sum(s) / len(s), 1) for b, s in buildings.items()},
        "checks": scores,
    }


@app.get("/quality/{building_id}")
def quality_for_building(building_id: str, session: SessionDep):
    """Score, check results and every problem found for one building."""
    checks = rows(
        session, "SELECT * FROM quality_score WHERE building_id = :b", b=building_id
    )
    if not checks:
        raise HTTPException(status_code=404, detail=f"No quality report for {building_id}")
    return {
        "building_id": building_id,
        "score": round(sum(c["score"] for c in checks) / len(checks), 1),
        "checks": checks,
        "issues": rows(
            session,
            "SELECT check_id, item, detail FROM quality_issue WHERE building_id = :b",
            b=building_id,
        ),
    }


@app.get("/audit-log")
def audit_log(
    session: SessionDep,
    table: str | None = None,
    record_id: str | None = None,
    limit: int = 50,
):
    """Who changed what, when and why. Newest first. Filter by table or record."""
    query = "SELECT * FROM audit_log WHERE 1 = 1"
    if table:
        query += " AND table_name = :table"
    if record_id:
        query += " AND record_id = :record_id"
    query += " ORDER BY id DESC LIMIT :limit"
    return rows(session, query, table=table, record_id=record_id, limit=limit)


@app.get("/", include_in_schema=False)
def home():
    """Opening the main address sends you to the /docs page."""
    return RedirectResponse(url="/docs")
