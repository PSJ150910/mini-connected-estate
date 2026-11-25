"""Mark our ID map against the private answer key, like a teacher marking a test.

Run with:  uv run python src/score_matching.py
"""

import pandas as pd

key = pd.read_csv("data/answer_key/answer_key.csv", dtype=str).fillna("")
id_map = pd.read_csv("data/processed/id_map.csv", dtype=str).fillna("")


def clean(name):
    return name.strip().casefold()  # '  AHU2 BLK A ' and 'AHU2 Blk A' count as the same


# Our answers: (source, cleaned name) -> set of IDs we chose
our_answer = {
    (row.source, clean(row.raw_name)): set(row.matched_id.split("|")) - {""}
    for row in id_map.itertuples()
}

# Every question in the key: one messy name and its true ID
questions = []
for row in key[key["kind"].isin(["asset", "room", "building"])].itertuples():
    for source, cell in [
        ("bms", row.bms_name),
        ("cafm", row.cafm_names),
        ("docs", row.documents),
    ]:
        for name in cell.split(" | "):
            if name:
                questions.append((row.kind, row.true_id, source, name))

marks, never_seen = [], []
for kind, true_id, source, name in questions:
    chosen = our_answer.get((source, clean(name)))
    if chosen is None:
        never_seen.append(f"{source}: {name} ({true_id})")
        continue  # this nickname never actually appears in the raw data
    marks.append(
        {
            "kind": kind,
            "true_id": true_id,
            "source": source,
            "name": name,
            "we_said": "|".join(sorted(chosen)) or "(no match)",
            "correct": true_id in chosen,
        }
    )
marks = pd.DataFrame(marks)

# Score 1: how many individual names did we get right?
print(
    f"Names matched correctly: {marks['correct'].sum()} / {len(marks)} "
    f"= {marks['correct'].mean():.1%}"
)
print(
    marks.groupby("source")["correct"]
    .agg(["sum", "count", "mean"])
    .round(3)
    .to_string()
)

# Score 2: how many key rows (assets, rooms, buildings) got EVERY name right?
rows_ok = marks.groupby("true_id")["correct"].all()
print(
    f"\nAssets/rooms/buildings fully correct: {rows_ok.sum()} / {len(rows_ok)} "
    f"= {rows_ok.mean():.1%}  (target 95%)"
)
print(
    f"Not scored: {len(key) - len(key[key['kind'] != 'fault'])} fault rows (those are for Module 4)"
)

if never_seen:
    print(
        f"\nSkipped {len(never_seen)} names in the key that never appear in the raw data:"
    )
    print("  " + "\n  ".join(never_seen))

wrong = marks[~marks["correct"]]
if len(wrong):
    print("\nMistakes to look at:")
    print(wrong.to_string(index=False))
