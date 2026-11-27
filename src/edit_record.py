"""Change one value in the database, the PROPER way: with your name and a reason.

Run with, for example:
    uv run python src/edit_record.py asset AHU-02 name "AHU 2, first floor plant room" --user Jaswanth --reason "Name checked on site"
"""

import argparse
import os

from sqlalchemy import create_engine, text

from audit import WATCHED

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///data/twin.db")

parser = argparse.ArgumentParser(description="Edit one value, with an audit trail.")
parser.add_argument("table", choices=list(WATCHED))
parser.add_argument("record_id", help="for example AHU-02")
parser.add_argument("column", help="for example name")
parser.add_argument("value", help="the new value")
parser.add_argument("--user", required=True, help="who is making the change")
parser.add_argument("--reason", required=True, help="why (an auditor will ask!)")
args = parser.parse_args()

# Never paste user text straight into SQL. Table and column come from a fixed list,
# and the values travel separately as :parameters (this stops 'SQL injection').
if args.column not in WATCHED[args.table] or args.column == "id":
    raise SystemExit(f"Column must be one of {WATCHED[args.table][1:]}")

engine = create_engine(DATABASE_URL)
with engine.begin() as conn:  # the name, the change and the log are saved together
    conn.execute(
        text("UPDATE app_user SET name = :name, reason = :reason WHERE id = 1"),
        {"name": args.user, "reason": args.reason},
    )
    changed = conn.execute(
        text(f"UPDATE {args.table} SET {args.column} = :value WHERE id = :id"),
        {"value": args.value, "id": args.record_id},
    ).rowcount
    # Put the name back to 'unknown', so the NEXT change can't borrow it by mistake
    conn.execute(text("UPDATE app_user SET name = 'unknown', reason = NULL WHERE id = 1"))

if changed == 0:
    raise SystemExit(f"No {args.table} called {args.record_id}. Nothing changed.")
print(f"Changed {args.table} {args.record_id}: {args.column} = {args.value!r}")
