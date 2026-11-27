"""AUDIT TRAIL: a permanent diary of every change to the important tables.

Run with:  uv run python src/audit.py        (rebuild.py runs it for you)

How it works:
  1. A table called audit_log. Rows are only ever ADDED, never changed or deleted.
  2. TRIGGERS: little rules stored INSIDE the database. "Whenever someone inserts,
     updates or deletes a row in asset, write a line in audit_log."
     They fire for every change, even one typed by hand in a database tool.
  3. WHO made the change: a database cannot know your name, so before editing,
     the program writes it in a one-row table called app_user. The triggers copy it.
     (PostgreSQL does the same idea with SET app.user = 'Jaswanth'.)
"""

import os

from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///data/twin.db")

# Which tables to watch, and their primary key column.
# Not 'reading': one million rows, and sensors are not edited by people.
WATCHED = {
    "asset": ["id", "name", "asset_type", "room_id", "building_id"],
    "room": ["id", "name", "building_id"],
    "document": ["id", "doc_type", "area_text", "inspected", "next_due"],
    "workorder": ["id", "asset_id", "room_id", "problem", "priority", "status", "cost"],
}

CREATE_TABLES = [
    """CREATE TABLE IF NOT EXISTS audit_log (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        changed_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now')),
        changed_by  TEXT NOT NULL,
        reason      TEXT,
        table_name  TEXT NOT NULL,
        record_id   TEXT NOT NULL,
        action      TEXT NOT NULL,       -- INSERT, UPDATE or DELETE
        old_values  TEXT,                -- JSON: the row BEFORE the change
        new_values  TEXT                 -- JSON: the row AFTER the change
    )""",
    # One row only: who is working right now, and why
    """CREATE TABLE IF NOT EXISTS app_user (
        id      INTEGER PRIMARY KEY CHECK (id = 1),
        name    TEXT NOT NULL,
        reason  TEXT
    )""",
    "INSERT OR IGNORE INTO app_user (id, name, reason) VALUES (1, 'unknown', NULL)",
    # The diary must never be rewritten: block UPDATE and DELETE on audit_log itself
    """CREATE TRIGGER IF NOT EXISTS audit_log_no_update BEFORE UPDATE ON audit_log
       BEGIN SELECT RAISE(ABORT, 'audit_log is append-only'); END""",
    """CREATE TRIGGER IF NOT EXISTS audit_log_no_delete BEFORE DELETE ON audit_log
       BEGIN SELECT RAISE(ABORT, 'audit_log is append-only'); END""",
]


def json_of(prefix, columns):
    """json_object('id', NEW.id, 'name', NEW.name, ...) : a row as JSON text."""
    pairs = ", ".join(f"'{c}', {prefix}.{c}" for c in columns)
    return f"json_object({pairs})"


def trigger_sql(table, columns, action):
    """Write the CREATE TRIGGER statement for one table and one action."""
    row = "OLD" if action == "DELETE" else "NEW"
    old = json_of("OLD", columns) if action != "INSERT" else "NULL"
    new = json_of("NEW", columns) if action != "DELETE" else "NULL"
    return f"""
    CREATE TRIGGER IF NOT EXISTS audit_{table}_{action.lower()}
    AFTER {action} ON {table}
    BEGIN
        INSERT INTO audit_log (changed_by, reason, table_name, record_id, action,
                               old_values, new_values)
        SELECT name, reason, '{table}', {row}.id, '{action}', {old}, {new}
        FROM app_user WHERE id = 1;
    END"""


def install(engine, tables=WATCHED):
    with engine.begin() as conn:  # begin() = one transaction, saved at the end
        for statement in CREATE_TABLES:
            conn.execute(text(statement))
        for table, columns in tables.items():
            for action in ["INSERT", "UPDATE", "DELETE"]:
                conn.execute(text(trigger_sql(table, columns, action)))


if __name__ == "__main__":
    if not DATABASE_URL.startswith("sqlite"):
        raise SystemExit("These triggers are written for SQLite. See the journal for PostgreSQL.")
    engine = create_engine(DATABASE_URL)
    install(engine)
    print(f"Audit log ready: watching {', '.join(WATCHED)} (insert, update, delete)")
