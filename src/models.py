"""The DATABASE DESIGN: one Python class = one table.

SQLModel turns these classes into real database tables for us.
Field(primary_key=True)  -> the unique ID of each row (like a roll number)
Field(foreign_key=...)   -> a link to a row in another table
"""

from datetime import datetime

from sqlmodel import Field, SQLModel


class Site(SQLModel, table=True):
    id: str = Field(primary_key=True)  # "GFA"
    name: str


class Building(SQLModel, table=True):
    id: str = Field(primary_key=True)  # "B1"
    name: str
    site_id: str = Field(foreign_key="site.id")


class Room(SQLModel, table=True):
    id: str = Field(primary_key=True)  # "B1-101"
    name: str
    building_id: str = Field(foreign_key="building.id")


class Asset(SQLModel, table=True):
    id: str = Field(primary_key=True)  # "AHU-02"
    name: str
    asset_type: str  # "AHU"
    room_id: str = Field(foreign_key="room.id")
    building_id: str = Field(foreign_key="building.id")


class Sensor(SQLModel, table=True):
    """One BMS 'point': one thing that is measured, e.g. Classroom 1 temperature."""

    id: str = Field(primary_key=True)  # the BMS column name, "BLKA_GF_CLS01_ZoneTemp"
    measure: str  # "ZoneTemp", "CO2", "Occ", "SAT", "FanStatus", "kWh"
    room_id: str | None = Field(default=None, foreign_key="room.id")
    asset_id: str | None = Field(default=None, foreign_key="asset.id")


class Reading(SQLModel, table=True):
    """One value from one sensor at one time. This table is BIG (about 1 million rows)."""

    sensor_id: str = Field(foreign_key="sensor.id", primary_key=True)
    timestamp: datetime = Field(primary_key=True)
    value: float


class WorkOrder(SQLModel, table=True):
    id: str = Field(primary_key=True)  # "WO-26001"
    raised: datetime | None
    completed: datetime | None
    date_warning: str  # e.g. "day and month may be swapped"
    asset_id: str | None = Field(default=None, foreign_key="asset.id")
    room_id: str | None = Field(default=None, foreign_key="room.id")
    raw_asset_name: str  # what the CAFM user typed, kept for checking
    raw_location: str
    problem: str
    priority: str
    status: str
    contractor: str
    cost: float | None


class Document(SQLModel, table=True):
    id: str = Field(primary_key=True)  # the file name
    doc_type: str  # "Gas Safety Certificate"
    area_text: str  # what the document calls the asset or area
    inspected: datetime | None
    next_due: datetime | None  # empty = never expires (manuals)


class DocumentLink(SQLModel, table=True):
    """Which asset or building each document is about.
    One document can cover two assets (the AHU 1 & 2 manual), so this is its own table."""

    document_id: str = Field(foreign_key="document.id", primary_key=True)
    entity_id: str = Field(primary_key=True)  # "AHU-01" or "B2"
    entity_kind: str  # "asset" or "building"


class Alias(SQLModel, table=True):
    """Every messy name we have seen, and the official ID it means (from match_ids.py)."""

    source: str = Field(primary_key=True)
    raw_name: str = Field(primary_key=True)
    official_id: str
    confidence: int
    method: str
