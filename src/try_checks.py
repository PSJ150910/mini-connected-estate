"""Try the checks one by one and look at the problems they find.

Run with:  uv run python src/try_checks.py
"""

from sqlmodel import create_engine

from quality_checks import (
    check_completed_jobs,
    check_reading_ranges,
    check_sensor_completeness,
    check_work_orders_valid,
    load_data,
)

engine = create_engine("sqlite:///data/twin.db")
data = load_data(engine)
print(f"Loaded {len(data['readings']):,} readings and {len(data['work_orders'])} jobs\n")

for name, found in [
    ("COMP-01 sensor completeness", check_sensor_completeness(data["readings"])),
    ("COMP-02 completed jobs", check_completed_jobs(data["work_orders"])),
    ("VALID-01 reading ranges", check_reading_ranges(data["readings"])),
    ("VALID-02 work orders valid", check_work_orders_valid(data["work_orders"])),
]:
    failed = found[~found["passed"]]
    print(f"{name}: {len(found)} checked, {len(failed)} failed")
    print(failed.head(3).to_string(index=False), "\n")
