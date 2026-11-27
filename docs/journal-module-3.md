## Module 3: Data trust checker

**Dates:** 25 to 27 Nov 2026
**Goal:** automatic checks that find bad data, a 0 to 100 trust score per building, and a permanent log of who changed what.
**Result:** done. 11 checks ran on 1,115 items and found 97 problems, including **both hidden faults from Module 1**. Building scores: **B1 92.5 GREEN, B2 81.0 AMBER, B3 94.9 GREEN**. My edit to AHU-02 shows up in `/audit-log` with my name, the time and my reason. **14/14 tests pass.**

---

### 1. Concepts I learned

#### Data governance and data quality
- **Data governance** = rules about data, plus proof that the rules are followed. If people can't trust the data, they won't use the twin.
- **Golden rule:** write the rule in plain English first (so a manager can agree), then in code. My rules are in `docs/data_rules.md`.

#### The 5 data quality dimensions
| Dimension | Meaning | My checks |
|---|---|---|
| Complete | nothing missing | COMP-01 sensors send 98% of readings, COMP-02 finished jobs have a date and cost |
| Unique | no duplicates | UNIQ-01 no asset listed twice, UNIQ-02 no job logged twice within 1 day |
| Valid | values make sense | VALID-01 readings physically possible, VALID-02 job ID/priority/status/cost/dates |
| Timely | still arriving, papers in date | TIME-01 no sensor silent > 2 h, TIME-02 no sensor stuck > 6 h, TIME-03 no expired certificate |
| Consistent | sources agree | CONS-01 rooms cool below 20 C at night, CONS-02 every boiler/lift/etc. has a certificate |

#### Pandera (rules as code)
- **Schema** = what a good table looks like, column by column (like college admission rules).
- `pa.Check.isin([...])` = value must be one of these. `str_matches(r"^WO-\d{5}$")` = a **regex** pattern. `nullable=False` = must not be empty.
- A **row-level check** looks at several columns at once: a job can't finish before it starts.
- `lazy=True` = find **all** problems, not just the first.

#### Time-series tricks in pandas
- `.diff()` = this row minus the previous one. On timestamps it gives the **gap** (silent sensor).
- **Run trick:** `value != previous value` then `.cumsum()` gives each run of the same value a number. Count the run length to find a **frozen (flat-lined)** sensor.
- `.duplicated(keep=False)` marks both copies of a duplicate.

#### Scoring
- Every check returns the same shape: **one row per item checked** (building, item, passed, detail).
- Pass rate per check = passed / checked x 100. **Building score = average of its check scores**, so 3 expired certificates count as much as 300 work orders and can't hide.
- **RAG status:** 90+ GREEN, 75 to 90 AMBER, below 75 RED.

#### Audit trail
- **Audit log** = who, when, what (before and after, as **JSON**), why.
- **Trigger** = a rule stored inside the database that fires on every INSERT, UPDATE or DELETE, even a hand edit in a database tool.
- **Who?** A database can't know my name, so `edit_record.py` writes it in a one-row `app_user` table first and the trigger copies it (PostgreSQL does the same with `SET app.user`). A sneaky edit without the tool is still logged, as `unknown`.
- **Append-only:** two more triggers block UPDATE and DELETE on `audit_log` itself. Even the owner can't rewrite the diary, which is why an auditor can trust it.
- **SQL injection:** never paste user text into SQL. Values travel as `:parameters`.

#### Automated testing (pytest)
- A test = tiny fake data where I already know the answer, run the check, `assert` the answer.
- **Regression:** I changed `MAX_FLAT` from 6 to 12 hours on purpose and `test_frozen_sensor_is_caught` went red at once (its fake sensor is stuck for 10 hours). Changed it back: 14 green.
- `tmp_path` gives a test its own throw-away database, so tests never touch `twin.db`.

#### API (query parameters)
- `/audit-log?record_id=AHU-02&limit=5`: the part after `?` gives options, like "biryani, less spicy".

#### Linux (WSL2) and signed software
- **Signed** software carries a company's digital stamp. Windows Smart App Control started blocking unsigned files: first uv's `python.exe`, then numpy's compiled `.pyd` files.
- **WSL2** = a real Ubuntu Linux inside Windows. Smart App Control doesn't touch Linux programs, and most data and cloud servers run Linux anyway.
- Linux words: distro, `sudo` (do as admin), `apt` (app store), `~` (home), `/mnt/c` (the Windows C: drive), pipe `|`, `cp -r`, `rm -rf` (careful!).
- **Remote development:** VS Code on Windows works inside Linux through the VS Code Server (bottom-left shows `WSL: Ubuntu-24.04`).

---

### 2. What I built

| File | What it does | Check |
|---|---|---|
| `docs/data_rules.md` | 11 rules in plain English | Agreed before coding |
| `src/quality_checks.py` | All 11 checks (Pandera, SQL, pandas) | Both hidden faults caught |
| `src/try_checks.py` | Runs every check and prints problems | 97 problems listed |
| `src/quality_report.py` | Scores per check and building, saves tables + report | B1 92.5, B2 81.0, B3 94.9 |
| `reports/quality_report.md` | Report for people (Ctrl+Shift+V in VS Code) | Score grid + problem list |
| `src/audit.py` | `audit_log` table + triggers on asset, room, document, workorder | Delete is blocked |
| `src/edit_record.py` | Edit one value with `--user` and `--reason` | AHU-02 logged as Jaswanth |
| `src/rebuild.py` | Now 6 steps: register, match, ETL, score, audit, quality | "All done" in one command |
| `tests/test_quality_checks.py` | 14 pytest tests | 14 passed in 1.5 s |
| `src/api.py` | New `/quality`, `/quality/{building_id}`, `/audit-log` | Name, time and reason returned |

#### What the checker found on my data
- 🎯 **Hidden fault 2:** Science Lab CO2 stuck at 612 ppm from 12 May 10:00, for 2,616 hours (TIME-02).
- 🎯 **Hidden fault 1:** Library warm on 18 nights from 10 March (CONS-01). The heating valve was stuck open.
- **Network outage:** all 18 Block B sensors silent for 48.2 hours at the same time (TIME-01). All sensors together = network, not 18 broken sensors.
- **9 of 18 certificates expired,** including Gas Safe for Boiler 1 and the Legionella risk assessment (TIME-03). In a real school, report the same day.
- **60 jobs with unclear dates** (VALID-02), the same ones Module 2 warned about.
- **3 completed jobs with no finish date** (COMP-02).
- **5 possible duplicate jobs** (UNIQ-02), the same fault typed with different names one day apart. **Flagged, not deleted:** a check reports, a human decides.
- VALID-01 found 0 impossible readings because the ETL already removed the `-999` glitches. A passing check is proof the cleaning works.

#### Which fix would help Block B most?
TIME-01 is at 0, worth 100/11 = about +9 points. But lost data can't be fixed; the real fix is an alert when a building goes quiet (Module 5). Renewing the 3 expired certificates (+5.5 points) is the fix a manager can do this week.

---

### 3. What broke and how I fixed it

| Problem | Cause | Fix | Lesson |
|---|---|---|---|
| `docs\data_rules.md` gave "module could not be loaded" | Typing a file name in PowerShell means "run this command" | `code docs\data_rules.md` or New File in VS Code | PowerShell runs commands, VS Code edits files |
| `SyntaxError: unterminated string literal` line 162 | Missing `"` before `P4 - Planned` | Added the quote | Read the traceback bottom-up; with quotes the mistake is left of the `^` |
| 7 typos in the Pandera schema | `pa.check` vs `pa.Check`, missing dot and comma, wrong column name `data_warning`, wrong ID pattern | Corrected block | Python is case-sensitive; column names must match exactly |
| My counts differed from the teacher's (60 vs 54) | The data is random, each copy differs | Trust my own output | |
| `Failed to spawn: python ... Application Control policy` | Smart App Control blocked the unsigned `.venv\Scripts\python.exe` | Installed signed Python 3.13 from python.org | `Get-AuthenticodeSignature` shows Valid / NotSigned |
| `uv sync` rebuilt `.venv` with 3.12 | `.python-version` still said 3.12 | `uv python pin 3.13` | Small config files control big behaviour |
| `DLL load failed while importing _common` (numpy) | Compiled numpy files blocked too | **Moved the project to WSL2 Ubuntu** | You can't fight a security policy one file at a time |
| `apt` "waiting for headers" | Slow download server | Waited | Patience; `ping` tests the network |
| Git credential helper `not found`, password refused | Wrong Windows path; GitHub stopped password login in 2021 | `gh auth login` (browser + one-time code) | Use tokens, the `gh` CLI handles them |
| Typed commands into the `gh` question box | It was still waiting for my answer | Ctrl+C, run again, arrows only | Wait for the `$` prompt |
| `GH007: push would publish a private email` | Commit used my Gmail, account has email privacy on | No-reply email + `git commit --amend --reset-author --no-edit` | GitHub protects you from spammers |

**Known limitation:** `rebuild.py` deletes `twin.db`, so the audit log starts empty after each rebuild. A real company never rebuilds the live database; in this project permanent corrections go in `data/manual/` files, which survive rebuilds. The audit triggers are written for SQLite; PostgreSQL would use a PL/pgSQL trigger function (an extra for later).

---

### 4. Command cheat sheet

```
# Open the project (Linux)
Start > Ubuntu
cd ~/projects/mini-connected-estate
code .

uv add pandera pytest tabulate
uv run python src/try_checks.py
uv run python src/quality_report.py
uv run python src/audit.py
uv run python src/edit_record.py asset AHU-02 name "AHU 2, first floor plant room" --user Jaswanth --reason "Name checked on site"
uv run python src/rebuild.py
uv run python -m pytest -v
uv run python -m uvicorn api:app --app-dir src --reload

# WSL2 setup (once)
wsl --install -d Ubuntu-24.04
sudo apt update && sudo apt upgrade -y
curl -LsSf https://astral.sh/uv/install.sh | sh
git config --global core.autocrlf input
git config core.fileMode false
sudo apt install gh -y
gh auth login
```
Browser (Windows): http://127.0.0.1:8000/docs → `/quality`, `/quality/B2`, `/audit-log?record_id=AHU-02`
