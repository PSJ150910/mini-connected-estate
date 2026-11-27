"""Run every data trust check, give each building a 0-100 score, save the report.

Run with:  uv run python src/quality_report.py
Creates:   reports/quality_report.md       (for people to read)
           reports/quality_issues.csv      (every failed item, for fixing)
           tables quality_score + quality_issue in the database (for the API)
"""

import os
import time
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from sqlmodel import create_engine

from quality_checks import load_data, run_all_checks

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///data/twin.db")
engine = create_engine(DATABASE_URL)


def score_table(results):
    """Pass rate (0-100) for every check in every building, plus the building score.
    Building score = the AVERAGE of its check scores, so every rule counts equally,
    whether it looked at 3 certificates or 300 work orders."""
    per_check = (
        results.groupby(["building_id", "check_id", "dimension", "rule"])["passed"]
        .agg(items="size", passed="sum")
        .reset_index()
    )
    per_check["score"] = (100 * per_check["passed"] / per_check["items"]).round(1)
    per_building = per_check.groupby("building_id")["score"].mean().round(1)
    return per_check, per_building


def grade(score):
    """Traffic light, like a school report."""
    return "GREEN" if score >= 90 else "AMBER" if score >= 75 else "RED"


if __name__ == "__main__":
    started = time.time()
    data = load_data(engine)
    print(f"Loaded {len(data['readings']):,} readings in {time.time() - started:.0f} s")

    results = run_all_checks(data)
    per_check, per_building = score_table(results)
    issues = results[~results["passed"]].drop(columns="passed")
    checked_at = datetime.now(UTC)

    # 1. Print a short summary on screen
    print(f"\nChecked {len(results):,} items, {len(issues)} problems found\n")
    for building, score in per_building.items():
        print(f"  {building}: {score:5.1f} / 100  {grade(score)}")
    print("\nWorst checks:")
    for row in per_check.sort_values("score").head(6).itertuples():
        print(f"  {row.building_id} {row.check_id:8} {row.score:5.1f}  {row.rule}")

    # 2. Save into the database, so the API can serve it (replace the old report)
    per_check.assign(checked_at=checked_at).to_sql(
        "quality_score", engine, if_exists="replace", index=False
    )
    issues.assign(checked_at=checked_at).to_sql(
        "quality_issue", engine, if_exists="replace", index=False
    )

    # 3. Save files for people
    Path("reports").mkdir(exist_ok=True)
    issues.to_csv("reports/quality_issues.csv", index=False)
    lines = [
        "# Data quality report: Greenfield Academy",
        f"Checked on {checked_at:%d %b %Y %H:%M} UTC. {len(results):,} items, "
        f"{len(issues)} problems.\n",
        "## Score per building\n",
        "| Building | Score | Grade |",
        "|---|---|---|",
    ]
    lines += [f"| {b} | {s} | {grade(s)} |" for b, s in per_building.items()]
    lines += ["\n## Score per check\n"]
    wide = per_check.pivot(index=["check_id", "rule"], columns="building_id", values="score")
    lines += [wide.reset_index().fillna("-").to_markdown(index=False)]
    lines += ["\n## Problems found\n"]
    lines += [
        issues[["building_id", "check_id", "item", "detail"]]
        .sort_values(["building_id", "check_id"])
        .to_markdown(index=False)
    ]
    Path("reports/quality_report.md").write_text("\n".join(lines), encoding="utf-8")
    print("\nSaved reports/quality_report.md and reports/quality_issues.csv")
    print(f"Finished in {time.time() - started:.0f} s")
