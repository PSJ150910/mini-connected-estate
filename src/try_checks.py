"""Run ALL the checks and show every problem they find.

Run with:  uv run python src/try_checks.py
"""

from sqlmodel import create_engine

from quality_checks import load_data, run_all_checks

engine = create_engine("sqlite:///data/twin.db")
data = load_data(engine)
results = run_all_checks(data)

summary = results.groupby(["check_id", "rule"])["passed"].agg(
    checked="size", passed="sum"
)
summary["failed"] = summary["checked"] - summary["passed"]
print(summary.to_string(), "\n")

# Show the problems from the new checks of Lesson 3
new_checks = ["UNIQ-01", "UNIQ-02", "TIME-01", "TIME-02", "TIME-03", "CONS-01", "CONS-02"]
problems = results[~results["passed"] & results["check_id"].isin(new_checks)]
print(problems[["check_id", "building_id", "item", "detail"]].to_string(index=False))
