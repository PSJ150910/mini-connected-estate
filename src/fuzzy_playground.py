"""Play with fuzzy matching: how similar are two pieces of text (0-100)?

Run with:  uv run python src/fuzzy_playground.py
"""

from rapidfuzz import fuzz

pairs = [
    ("AHU2 Blk A", "AHU2 Blk A"),  # identical
    ("AHU2 Blk A", "ahu2 blk a"),  # only capitals differ
    ("Staffroom", "Staff Room"),  # one space missing
    ("Class 1", "Classroom 1"),  # short form
    ("Lab", "Science Lab"),  # part of the name
    ("Kitchen / Canteen", "Canteen"),  # extra words
    ("Classroom 1", "Classroom 2"),  # DANGER: looks almost the same!
    ("Front office", "Head Office"),  # DANGER: different rooms
    ("Boiler B", "Boiler Blk B"),
]

print(f"{'text 1':20} {'text 2':14} {'ratio':>6} {'token_set':>10} {'WRatio':>7}")
for a, b in pairs:
    print(
        f"{a:20} {b:14} {fuzz.ratio(a, b):6.0f} "
        f"{fuzz.token_set_ratio(a, b):10.0f} {fuzz.WRatio(a, b):7.0f}"
    )
