"""ENTITY RESOLUTION: work out which official ID every messy name refers to.

Reads the 3 messy sources (BMS, CAFM, documents) and the master register,
and writes one "ID map": messy name -> official ID, with a confidence score.
Anything the computer is unsure about goes on a review list for a human.

It must NEVER read data/answer_key/ (that would be cheating).

Run with:  uv run python src/match_ids.py
Creates:   data/processed/id_map.csv  and  data/processed/review_list.csv
"""

import re
from pathlib import Path

import pandas as pd
from pypdf import PdfReader
from rapidfuzz import fuzz

register = pd.read_csv("data/processed/register.csv", dtype=str).fillna("")
assets = register[register["kind"] == "asset"]
rooms = register[register["kind"] == "room"]

# ---------------------------------------------------------------
# 1. THE GLOSSARY: short forms and nicknames -> one standard word
#    (Every real data team keeps a list like this.)
# ---------------------------------------------------------------
GLOSSARY = {
    "blk": "block",
    "blka": "block a",
    "blkb": "block b",
    "blkc": "block c",
    "b1": "block a",
    "b2": "block b",
    "b3": "block c",  # BMS installer's codes
    "rm": "room",
    "cls": "classroom",
    "sci": "science",
    "lib": "library",
    "ict": "it suite",
    "off": "office",
    "staffroom": "staff room",
    "kitchen": "canteen",
    "hw": "hot water",
    "hws": "hot water",
    "elec": "electricity",
    "no": "",
    "gf": "",
    "1f": "",
    "1st": "",
}
PHRASES = {"front office": "reception"}


def normalise(text):
    """'  AHU2 Blk A ' -> 'ahu 2 block a'. Same idea for every source."""
    text = str(text).lower().replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)  # punctuation and _ become spaces
    words = [GLOSSARY.get(word, word) for word in text.split()]
    text = " ".join(words)
    text = re.sub(r"([a-z])(\d)", r"\1 \2", text)  # 'ahu2' -> 'ahu 2'
    text = re.sub(r"(\d)([a-z])", r"\1 \2", text)  # '30kwp' -> '30 kwp'
    text = " ".join(GLOSSARY.get(word, word) for word in text.split())  # 'cls 01'
    for old, new in PHRASES.items():
        text = text.replace(old, new)
    return " ".join(text.split())


def has_word(text, word):
    """True if word (or its plural) appears as a whole word in text."""
    return re.search(rf"\b{word}s?\b", text) is not None


# ---------------------------------------------------------------
# 2. CLUES WE CAN READ FROM A NAME: asset type, building, number
# ---------------------------------------------------------------
TYPE_WORDS = {
    "AHU": ["ahu", "air handler", "air handling"],
    "BLR": ["boiler"],
    "CAL": ["calorifier", "hot water"],
    "DB": ["db", "mdb", "distribution board"],
    "FAP": ["fire panel", "fire alarm", "fa panel", "facp"],
    "MTR": ["meter", "mtr"],
    "PV": ["solar", "pv"],
    "LIFT": ["lift"],
}
LETTER_TO_BUILDING = {"a": "B1", "b": "B2", "c": "B3"}
COMMON_WORDS = {"block", "room", "and", "main", "plant", "floor", "unit"}


def learn_building_words():
    """Words from building and room names that belong to ONE building only.
    e.g. 'library' -> B2, 'admin' -> B3. Learned from the BIM model itself."""
    seen = {}
    for _, row in register[register["kind"] != "asset"].iterrows():
        for word in normalise(row["name"]).split():
            seen.setdefault(word, set()).add(row["building_id"])
    return {
        w: b.pop()
        for w, b in seen.items()
        if len(b) == 1 and w not in COMMON_WORDS and not w.isdigit() and len(w) > 1
    }


BUILDING_WORDS = learn_building_words()


def find_types(text):
    return {
        t for t, words in TYPE_WORDS.items() if any(has_word(text, w) for w in words)
    }


def find_building(text):
    """Every word votes for a building. Returns the winner, or '' if unclear."""
    votes = {}
    for word in text.split():
        building = LETTER_TO_BUILDING.get(word) or BUILDING_WORDS.get(word)
        if building:
            votes[building] = votes.get(building, 0) + 1
    if not votes:
        return ""
    best = max(votes.values())
    winners = [b for b, v in votes.items() if v == best]
    return winners[0] if len(winners) == 1 else ""


def find_numbers(text):
    """Small numbers 1-9 are unit numbers ('AHU 2'). Big ones ('150') are model numbers."""
    return [int(n) for n in re.findall(r"\b\d+\b", text) if 1 <= int(n) <= 9]


# ---------------------------------------------------------------
# 3. THE MATCHERS
#    Each one returns (matched IDs, confidence 0-100, how it decided)
# ---------------------------------------------------------------
def match_asset(raw):
    text = normalise(raw)
    types = find_types(text)
    if len(types) != 1:
        return [], 0, f"asset type unclear: {sorted(types)}"
    asset_type = types.pop()
    building = find_building(text)
    numbers = find_numbers(text)

    # "Blocking": only compare against assets of the same type (and building)
    candidates = assets[assets["asset_type"] == asset_type]
    if building:
        candidates = candidates[candidates["building_id"] == building]

    if len(candidates) == 1:
        return list(candidates["id"]), 100, "only one possible asset"
    if numbers:
        column = "number_in_building" if building else "number_overall"
        picked = candidates[candidates[column].astype(int).isin(numbers)]
        if len(picked) > 0:
            return list(picked["id"]), 100, f"matched unit number {numbers}"
    return [], 0, f"{len(candidates)} possible assets: {list(candidates['id'])}"


def match_room(raw):
    text = normalise(raw)
    # Rule 1: a room number like 'room 105' maps straight to B1-105
    for number in re.findall(r"\b[1-3]0\d\b", text):
        found = rooms[rooms["id"].str.endswith(number)]
        if len(found) == 1:
            return list(found["id"]), 100, "room number"

    # Rule 2: fuzzy-compare the words with every room name
    building = find_building(text)
    numbers = find_numbers(text)
    words = " ".join(
        w
        for w in text.split()
        if w not in LETTER_TO_BUILDING and w != "block" and not w.isdigit()
    )
    best_id, best_score = "", 0
    for _, room in rooms.iterrows():
        if building and room["building_id"] != building:
            continue
        room_numbers = find_numbers(normalise(room["name"]))
        if numbers and room_numbers and room_numbers != numbers:
            continue  # 'Classroom 1' must not match 'Classroom 2'
        room_words = re.sub(r"\d", "", normalise(room["name"])).strip()
        score = fuzz.WRatio(words, room_words)
        if score > best_score:
            best_id, best_score = room["id"], score
    return [best_id], round(best_score), "fuzzy name match"


def match_building(raw):
    building = find_building(normalise(raw))
    return (
        ([building], 100, "building clue") if building else ([], 0, "no building clue")
    )


# ---------------------------------------------------------------
# 4. COLLECT EVERY MESSY NAME FROM THE 3 SOURCES
#    (source, raw name, what it should be, text to match on)
# ---------------------------------------------------------------
names = []

ROOM_SUFFIXES = ("_ZoneTemp", "_CO2", "_Occ")
ASSET_SUFFIXES = ("_SAT", "_FanStatus")
for path in sorted(Path("data/raw/bms").glob("*.csv")):
    names.append(("bms", path.name, "building", path.stem))
    for column in pd.read_csv(path, nrows=0).columns[1:]:  # skip 'Timestamp'
        point = column
        for suffix in ROOM_SUFFIXES + ASSET_SUFFIXES:
            point = point.removesuffix(suffix)
        kind = "room" if column.endswith(ROOM_SUFFIXES) else "asset"
        names.append(("bms", point, kind, point))

work_orders = pd.read_csv("data/raw/cafm/work_orders.csv", dtype=str).fillna("")
for name in work_orders["Asset"].str.strip().unique():
    if name:
        names.append(("cafm", name, "asset", name))
for name in work_orders["Location"].str.strip().unique():
    if name:
        names.append(("cafm", name, "room", name))

for path in sorted(Path("data/raw/docs").glob("*.pdf")):
    page_text = PdfReader(path).pages[0].extract_text()
    found = re.search(r"Equipment / Area: (.+)", page_text)
    area = found.group(1).strip() if found else ""
    kind = "asset" if find_types(normalise(area)) else "building"
    names.append(("docs", path.name, kind, area))

# ---------------------------------------------------------------
# 5. MATCH THEM ALL AND SAVE
# ---------------------------------------------------------------
MATCHERS = {"asset": match_asset, "room": match_room, "building": match_building}
REVIEW_BELOW = 85  # confidence under this = a human should check it

# A human's answers to earlier review questions always win over the computer
decisions_file = Path("data/manual/review_decisions.csv")
decisions = {}
if decisions_file.exists():
    for row in pd.read_csv(decisions_file, dtype=str).itertuples():
        decisions[(row.source, row.raw_name)] = row.matched_id

results = []
for source, raw_name, kind, text in dict.fromkeys(names):  # dict.fromkeys drops repeats
    if (source, raw_name) in decisions:
        ids, confidence, method = (
            decisions[(source, raw_name)].split("|"),
            100,
            "human decision",
        )
    else:
        ids, confidence, method = MATCHERS[kind](text)
    results.append(
        {
            "source": source,
            "raw_name": raw_name,
            "kind": kind,
            "text_used": text,
            "matched_id": "|".join(ids),
            "confidence": confidence,
            "method": method,
            "needs_review": confidence < REVIEW_BELOW,
        }
    )

id_map = pd.DataFrame(results)
id_map.to_csv("data/processed/id_map.csv", index=False)
review = id_map[id_map["needs_review"]]
review.to_csv("data/processed/review_list.csv", index=False)

print(id_map.groupby(["source", "kind"]).size().to_string())
print(f"\nSaved data/processed/id_map.csv: {len(id_map)} names matched")
print(f"{len(review)} names need a human to check (data/processed/review_list.csv)")
if len(review):
    print(
        review[["source", "raw_name", "matched_id", "confidence", "method"]].to_string(
            index=False
        )
    )
