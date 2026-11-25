"""Ask the database questions in SQL. The magic: data from 4 systems joined by ONE ID.

Run with:  uv run python src/ask_database.py
"""

import sqlite3

import pandas as pd

db = sqlite3.connect("data/twin.db")


def ask(title, sql):
    print(f"\n=== {title} ===")
    print(pd.read_sql(sql, db).to_string(index=False))


ask(
    "How many rows in each table?",
    """
    SELECT 'asset' AS table_name, COUNT(*) AS rows FROM asset
    UNION ALL SELECT 'room', COUNT(*) FROM room
    UNION ALL SELECT 'sensor', COUNT(*) FROM sensor
    UNION ALL SELECT 'reading', COUNT(*) FROM reading
    UNION ALL SELECT 'workorder', COUNT(*) FROM workorder
    UNION ALL SELECT 'document', COUNT(*) FROM document
""",
)

ask(
    "AHU-02: where is it? (BIM)",
    """
    SELECT asset.id, asset.name, room.name AS room, building.name AS building
    FROM asset
    JOIN room ON asset.room_id = room.id
    JOIN building ON asset.building_id = building.id
    WHERE asset.id = 'AHU-02'
""",
)

ask(
    "AHU-02: its sensors, average value (BMS)",
    """
    SELECT sensor.id AS sensor, ROUND(AVG(reading.value), 2) AS avg_value,
           COUNT(*) AS readings
    FROM sensor JOIN reading ON reading.sensor_id = sensor.id
    WHERE sensor.asset_id = 'AHU-02'
    GROUP BY sensor.id
""",
)

ask(
    "AHU-02: repair jobs (CAFM), last 5",
    """
    SELECT id, raised, raw_asset_name AS typed_as, problem, status
    FROM workorder WHERE asset_id = 'AHU-02'
    ORDER BY raised DESC LIMIT 5
""",
)

ask(
    "AHU-02: documents (PDFs)",
    """
    SELECT document.id, document.doc_type
    FROM documentlink JOIN document ON documentlink.document_id = document.id
    WHERE documentlink.entity_id = 'AHU-02'
""",
)

ask(
    "Work orders with date warnings",
    """
    SELECT date_warning, COUNT(*) AS jobs FROM workorder
    WHERE date_warning != '' GROUP BY date_warning
""",
)
