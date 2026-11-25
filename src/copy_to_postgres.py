"""Copy the whole SQLite database into PostgreSQL + TimescaleDB (running in Docker).

SQLite = one file, great for learning on your laptop.
PostgreSQL = a real database SERVER: many users and programs at once, used by companies.
TimescaleDB = an add-on that makes PostgreSQL very fast for time series (our readings).

Start the database first:  docker compose up -d
Run with:                  uv run python src/copy_to_postgres.py
"""

import sqlite3
import time

import pandas as pd
from sqlalchemy import text
from sqlmodel import SQLModel, create_engine

import models  # noqa: F401  (loading it tells SQLModel about our 10 tables)

POSTGRES_URL = "postgresql+pg8000://twin:twin_local_only@localhost:5432/twin"
postgres = create_engine(POSTGRES_URL)
sqlite = sqlite3.connect("data/twin.db")

# ---------------------------------------------------------------
# 1. MAKE EMPTY TABLES (same design as SQLite, from models.py)
# ---------------------------------------------------------------
SQLModel.metadata.drop_all(postgres)  # start fresh every time
SQLModel.metadata.create_all(postgres)

# ---------------------------------------------------------------
# 2. TURN 'reading' INTO A HYPERTABLE
#    TimescaleDB secretly splits it into weekly pieces ("chunks"),
#    so questions like "last week's readings" only look at one piece.
# ---------------------------------------------------------------
with postgres.begin() as connection:
    connection.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb"))
    connection.execute(
        text(
            "SELECT create_hypertable('reading', by_range('timestamp', INTERVAL '7 days'))"
        )
    )

# ---------------------------------------------------------------
# 3. COPY EVERY TABLE. Parents first (building before room), because a
#    room's building_id must point to a building that already exists.
# ---------------------------------------------------------------
TABLES = {  # table name -> its date columns
    "site": [],
    "building": [],
    "room": [],
    "asset": [],
    "alias": [],
    "sensor": [],
    "document": ["inspected", "next_due"],
    "documentlink": [],
    "workorder": ["raised", "completed"],
    "reading": ["timestamp"],
}
for table, date_columns in TABLES.items():
    start = time.time()
    rows = pd.read_sql(f"SELECT * FROM {table}", sqlite)
    for column in date_columns:
        rows[column] = pd.to_datetime(rows[column]).dt.tz_localize("UTC")
    rows.to_sql(
        table,
        postgres,
        if_exists="append",
        index=False,
        method="multi",
        chunksize=10_000,
    )
    print(f"{table:13} {len(rows):>9,} rows  ({time.time() - start:.0f} s)")

# ---------------------------------------------------------------
# 4. CHECK: ask TimescaleDB how it stored the readings
# ---------------------------------------------------------------
with postgres.connect() as connection:
    chunks = connection.execute(
        text(
            "SELECT count(*) FROM timescaledb_information.chunks WHERE hypertable_name = 'reading'"
        )
    ).scalar()
    weekly = connection.execute(
        text("""
        SELECT time_bucket('1 week', timestamp) AS week, ROUND(AVG(value)::numeric, 1) AS avg_temp
        FROM reading WHERE sensor_id = 'BLKB_GF_LIBRARY_ZoneTemp'
        GROUP BY week ORDER BY week LIMIT 5
    """)
    ).fetchall()
print(f"\nThe readings table is split into {chunks} weekly chunks")
print("Library: average temperature per week (time_bucket is a TimescaleDB function):")
for week, avg_temp in weekly:
    print(f"  week of {week:%d %b}: {avg_temp} C")
