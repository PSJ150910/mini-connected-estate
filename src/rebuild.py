"""ONE COMMAND to rebuild the whole database from the raw data.

Run with:  uv run python src/rebuild.py
"""

import subprocess
import sys

STEPS = [
    "build_register.py",  # 1. golden list from the BIM model
    "match_ids.py",  # 2. messy names -> official IDs
    "load_database.py",  # 3. ETL into data/twin.db
    "score_matching.py",  # 4. mark the matching against the answer key
]

for step in STEPS:
    print(f"\n----- {step} -----")
    result = subprocess.run([sys.executable, f"src/{step}"])
    if result.returncode != 0:
        sys.exit(f"Stopped: {step} failed. Fix it and run again.")
print("\nAll done: data/twin.db is rebuilt.")
