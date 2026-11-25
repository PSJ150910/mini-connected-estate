## Module 2: Connect the systems

**Date:** 25 Nov 2026
**Goal:** teach the computer that names like `AHU2 Blk A`, `B1_AHU2` and `AHU/A/02` are the same machine, put all four data sources into one database, and open it through a web API.
**Result:** done. Matching scored **100%** against the answer key (target 95%). One command rebuilds the whole database. `/assets/AHU-02` returns data from BIM, BMS, CAFM and PDFs in one answer.

---

### 1. Concepts I learned

#### Entity resolution
- Working out that different names mean the same real thing. Banks use it for customers; in buildings it is the core skill of a digital twin.
- The recipe used in industry: **rules first, fuzzy second, human last.**

#### Master register (golden record)
- One official list that everything is matched to. We chose the **BIM model** as the source of truth: 3 buildings, 18 rooms, 20 assets = 41 rows.
- Helper columns: `number_overall` (AHU-03 is AHU number 3 on campus) and `number_in_building` (AHU-03 is AHU number 1 in Block B, which is why the BMS calls it `B2_AHU1`).

#### Fuzzy matching (RapidFuzz)
| Scorer | Looks at | Good for |
|---|---|---|
| `ratio` | letters in order | typos |
| `token_set_ratio` | whole words, any order | `Lab` vs `Science Lab` |
| `WRatio` | tries everything, keeps the best | everyday use |

Three lessons from the playground:
1. `AHU2 Blk A` vs `ahu2 blk a` scored only **50**, so **normalise** first (lowercase, remove symbols, `blk` to `block`).
2. `Classroom 1` vs `Classroom 2` scored **91**, so **numbers must match exactly** (strict rule).
3. `Front office` = Reception can't be found from letters, so keep a **glossary** of nicknames.

#### How my matcher works
1. **Normalise** the name.
2. **Read clues:** asset type (ahu, boiler, lift...), building (letter, or words like "library" that the computer learned from the BIM model), unit number (small numbers only; `Evomax 150` is a model number).
3. **Blocking:** only compare with assets of the same type and building.
4. **Decide:** one candidate = match; two = use the number; rooms use WRatio + strict numbers.
5. **Confidence 0 to 100.** Below 85 goes on `review_list.csv` for a human (**human-in-the-loop**).
- Human decisions go in `data/manual/review_decisions.csv` (who, what, why = **audit trail**), and the matcher always obeys them.

#### Databases and SQL
- **Table** = one sheet. **Primary key** = unique ID of a row (like a roll number). **Foreign key** = a column that points to another table.
- **SQL** = the language for asking questions. **JOIN** = connect two tables using a matching ID.
- 10 tables: site, building, room, asset, sensor, reading, workorder, document, documentlink (one PDF can cover two assets), alias.
- **SQLite** = database in one file. **SQLModel** = tables written as Python classes.

#### ETL pipeline
- **Extract** raw files, **Transform** (clean + swap names for official IDs), **Load** into the database.
- Cleaning: duplicate BMS rows and jobs removed, `-999` removed, Block C day/month dates, `£` removed from costs, mixed UK/US dates resolved using the export period (unclear ones get a warning, not a guess).
- **Wide to long:** one column per sensor became one row per reading (998,478 rows).
- **Times stored in UTC** (the BMS clock doesn't jump in summer).
- **One command** (`rebuild.py`) runs everything: register, matching, ETL, scoring.

#### Brick Schema
- Free, open dictionary for buildings (`brick:AHU`, `brick:Zone_Air_Temperature_Sensor`).
- Facts written as **triples**: subject, relation, object (`AHU-02 feeds Zone AHU-02`).
- **SPARQL** = SQL for triples. Asked: "temperature sensors in rooms fed by AHU-02" and got B1-105, B1-106, B1-107.
- Brick has no exact class for a distribution board yet, so I used `Electrical_Equipment`.

#### COBie
- Standard Excel handover sheet: Facility, Floor, Space, Type, Component, Document. Every row starts with Name, CreatedBy, CreatedOn.
- `O&M_AHU_1_2` appears twice in the Document sheet because one manual covers two AHUs.

#### Docker, PostgreSQL, TimescaleDB
- **Container** = a small separate computer inside my laptop. **Image** = the ready-made recipe (image = recipe, container = the dish).
- **Docker Compose** = one settings file (`docker-compose.yml`), one command: `docker compose up -d`.
- **PostgreSQL** = real database server. **TimescaleDB** = add-on for time series. **Hypertable** = readings cut into weekly **chunks** (27 of them). `time_bucket` groups readings by week.
- **Driver** = translator between Python and the database. I used **pg8000** (pure Python).

#### APIs, REST and FastAPI
- API = restaurant menu: other programs order from the menu, never touch the kitchen (database).
- **REST**: each address is a thing (`/buildings`, `/assets/AHU-02`). Answers come back as **JSON**.
- **FastAPI** builds the **/docs** page (Swagger UI) by itself. **Uvicorn** = the web server.
- Status codes: **200** success, **404** not found, **500** server bug.
- **Environment variable** `DATABASE_URL` switches the same API from SQLite to PostgreSQL with no code change.

---

### 2. What I built

| Script | What it does | Check |
|---|---|---|
| `src/build_register.py` | Golden list from the IFC model | 41 rows |
| `src/fuzzy_playground.py` | Compare RapidFuzz scorers | Capitals = 50, Classroom 1 vs 2 = 91 |
| `src/match_ids.py` | Messy names to official IDs + review list | 143 names, 1 sent to a human |
| `data/manual/review_decisions.csv` | My decision: Evomax manual to BLR-01 | 0 left to review |
| `src/score_matching.py` | Mark against the answer key | **134/134 names, 38/38 rows = 100%** |
| `src/models.py` | Database design (10 tables) | Tables created |
| `src/load_database.py` | ETL into `data/twin.db` | 998,478 readings, 303 jobs, 24 docs |
| `src/ask_database.py` | SQL questions with JOINs | AHU-02 from all 4 systems |
| `src/rebuild.py` | One command for everything | "All done", 100% |
| `src/make_brick.py` | Brick model `campus_brick.ttl` | 338 triples, SPARQL answer |
| `src/make_cobie.py` | `reports/cobie_handover.xlsx` | 6 sheets |
| `docker-compose.yml` | PostgreSQL 17 + TimescaleDB | `twin-db` Up |
| `src/copy_to_postgres.py` | SQLite to PostgreSQL hypertable | 27 weekly chunks, 148 s |
| `src/api.py` | FastAPI with 6 endpoints | `/assets/AHU-02` returns everything |

#### Interesting things I noticed
- 2 nicknames in the answer key (`Air Handler 2 Blk A`, `Hall`) never appeared in the real data, so they couldn't be marked.
- The Evomax boiler manual says "all blocks", so the computer correctly refused to guess.
- About 60 repair jobs have dates where day and month can't be told apart. They got warnings for Module 3.
- The weekly Library temperature jumped from 18 C to 23 C from 9 March: **hidden fault 1** showed up by itself.

---

### 3. What broke and how I fixed it

| Problem | Cause | Fix | Lesson |
|---|---|---|---|
| `ImportError: DLL load failed ... _util_cy` | Smart App Control blocked SQLAlchemy's compiled speed-up file | Installed the pure Python SQLAlchemy wheel (`py3-none-any`) with `uv add "sqlalchemy @ <url>"` | Many libraries have a pure Python version. Test each compiled library (`import pydantic_core` worked) |
| `Failed to spawn: uvicorn` | Smart App Control blocked the `uvicorn.exe` launcher made by uv | `uv run python -m uvicorn ...` | `python -m <tool>` avoids unsigned launchers |
| Chose pg8000, not psycopg | psycopg's binary has compiled files that might be blocked | Pure Python driver pg8000 | Pick tools that fit your machine's rules |
| Terminal looked frozen while copying to PostgreSQL | 1 million rows take time, and the copy is saved in one transaction at the end | Waited (148 s) | Long steps need patience; output comes at the end |
| `/rooms/classroom 1` returned 404 | The endpoint needs the official ID (`B1-101`) | Use `/resolve?name=Classroom 1` first | A clear error is better than a wrong guess |
| `twin.db` is about 120 MB | GitHub limit is 100 MB | Added `data/twin.db` and `data/processed/` to `.gitignore` | Save the code, not what the code produces |

---

### 4. Command cheat sheet

```
uv add rapidfuzz pypdf sqlmodel brickschema openpyxl pg8000 fastapi uvicorn
uv add "sqlalchemy @ https://files.pythonhosted.org/packages/7a/ee/9926603a1f7e88b41bc0d1e068e889fc84981553fb4e6037426d6b174da3/sqlalchemy-2.1.9-py3-none-any.whl"
uv run python src/rebuild.py
uv run python src/ask_database.py
uv run python src/make_brick.py
uv run python src/make_cobie.py
docker compose up -d
docker ps
uv run python src/copy_to_postgres.py
uv run python -m uvicorn api:app --app-dir src --reload
$env:DATABASE_URL = "postgresql+pg8000://twin:twin_local_only@localhost:5432/twin"
```
Browser: http://127.0.0.1:8000/docs
