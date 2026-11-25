# Learning journal

## Module 0: Engineer's toolkit

**Dates:** 19 Nov 2026 (evening) and 23 Nov 2026
**Goal:** set up my laptop like a professional developer's, learn Python basics, and publish my first script on GitHub.
**Result:** done. Repo is live at https://github.com/PSJ150910/mini-connected-estate

---

### 1. My setup

| Item | Details |
|---|---|
| Laptop | Windows 11, Intel i7-13620H, 24 GB RAM, NVIDIA RTX 5050 (8 GB) |
| Project folder | `C:\Users\saija\projects\mini-connected-estate` |
| GitHub repo | `PSJ150910/mini-connected-estate` (public) |

| Tool | Version | What it does |
|---|---|---|
| VS Code | 1.146.0 | Code editor: where I write and run code |
| Git | 2.56.0 | Saves snapshots (commits) of my work |
| Python | 3.12.15 (via uv) | The programming language. 3.14 is also installed, but the project uses 3.12 |
| uv | 0.13.5 | Installs Python versions and packages, manages the virtual environment |
| Docker | 29.7.2 | Runs software inside containers |
| winget | 1.29 | Windows' built-in app installer |
| WSL 2 | installed on Day 1 | Linux inside Windows. Docker needs it |
| Ruff | 0.17.6 | Formats my code and checks it for mistakes |

VS Code extensions: Python, Jupyter, Rainbow CSV.

---

### 2. Concepts I learned

#### The terminal
- A window where I type commands instead of clicking. On Windows it's Windows Terminal running PowerShell.
- A command = program name + options. Example: `git --version` runs git and asks for its version.
- The prompt (`PS C:\Users\saija\projects\mini-connected-estate>`) shows **which folder** I'm in. Commands act on that folder.
- A new terminal always starts in my home folder (`C:\Users\saija`).
- Don't work in an Administrator terminal unless a step really needs it (like installing WSL). The `C:\WINDOWS\System32` prompt means admin.
- Warning = "heads up". Error = "this failed". Only errors stop me.
- Commands that print nothing usually succeeded.

#### Python versions
- Newest isn't always best. Libraries need time to support a new version, so companies often use one that's a year or two old.
- uv keeps several Python versions side by side and gives each project the one it needs (`.python-version` file).

#### Virtual environments
- A private box (`.venv` folder) holding one Python plus only that project's packages, so projects can't break each other.
- uv creates it automatically on the first `uv run`.
- `(mini-connected-estate)` at the start of the VS Code terminal prompt means the box is activated. VS Code does this automatically.
- I always run code with `uv run ...`, which uses the right box either way.

#### Project files created by uv
| File | Purpose |
|---|---|
| `pyproject.toml` | Project ID card: name, Python version, packages needed |
| `.python-version` | Pins the project to Python 3.12 |
| `uv.lock` | Exact versions of every package, so the project installs the same on any computer |
| `src/mini_connected_estate/` | "src layout": the modern standard place for the project's code |
| `README.md` | The project's front page on GitHub |

#### Folder layout
| Folder | What goes in it |
|---|---|
| `data/` | Raw data files |
| `src/` | Main code |
| `tests/` | Automatic checks |
| `notebooks/` | Analysis notebooks |
| `docs/` | Journal and reports |

Git tracks files, not folders, so empty folders need a placeholder file called `.gitkeep`.

#### Git and GitHub
- **Git** (on my laptop) saves **commits**: snapshots I can always go back to, like drawing revisions.
- **GitHub** (website) stores an online copy called the **remote**. It's my backup and my portfolio.
- **Repository (repo):** a project folder tracked by Git.
- **Clone:** download a repo from GitHub, already linked to it. **origin** = the nickname for that online copy.
- The three steps to save work:
  1. `git add` = stage (pack the parcel)
  2. `git commit -m "message"` = seal and label the parcel, saved on the laptop
  3. `git push` = send the parcel to GitHub
- Each commit gets a unique ID (for example `0d54928`).
- `git push -u origin main` the first time links my `main` branch to GitHub. After that, plain `git push` works.
- Git signs every commit with my name and email. I use GitHub's private **noreply** email so my real email stays private.
- Git Credential Manager handles GitHub sign-in through the browser. Never paste passwords into the terminal.
- "LF will be replaced by CRLF" warnings are harmless. Windows and Linux end lines differently, and Git converts automatically.

#### .gitignore
A list of things Git must never save:
- things that can be rebuilt (`.venv/`)
- junk files (`__pycache__/`, `*.pyc`)
- **secrets** (`.env`), because bots scan GitHub for leaked passwords and keys

`*` is a wildcard meaning "anything".

#### Docker
- **Container:** a sealed box holding a program and everything it needs, so it runs the same on any computer.
- **Image:** the frozen recipe (like a BIM family). **Container:** a running copy made from it (like a placed instance).
- **Docker Hub:** the public library of images. `docker run` **pulls** an image from there if I don't have it.
- Docker has two parts: the **client** (the `docker` command, a messenger) and the **engine/daemon** (does the real work, started by Docker Desktop).
- On Windows, the engine runs inside **WSL 2**.

#### Windows security: Smart App Control
- Blocks small unsigned programs (error 4551, "Application Control policy").
- It blocked two Python shortcut files, which was harmless because uv uses the real Python.
- Keep it on. Once it's turned off, it can't be turned back on without resetting Windows.

#### VS Code
- **Editor (top area):** file contents go here. Save with **Ctrl+S**. A white dot on the tab means unsaved.
- **Terminal (bottom area):** commands go here. Open it with **Ctrl+`**. It opens inside the project folder.
- `code .` opens the current folder in VS Code.
- Extensions: check who made one and how many people use it before installing.

#### Markdown
- `#` big heading, `##` smaller heading, `-` bullet point, backticks for `code`.
- GitHub shows `.md` files as formatted pages.

---

### 3. Python basics

#### Variables and types
```python
room_name = "Classroom 1"   # text (string)
people = 28                 # whole number (int)
temperature = 21.5          # decimal number (float)
print(f"{room_name} is {temperature} C with {people} people")
```
- A variable is a labelled box holding a value.
- Python keeps exactly what I type: `24` is an int, `24.0` is a float. Use decimals for temperatures.
- An **f-string** (`f"..."`) replaces `{name}` with the value.

#### Lists
```python
temperatures = [21.5, 24.0, 19.8, 22.3, 25.1]
temperatures[0]      # first item: 21.5 (counting starts at 0)
temperatures[-1]     # last item: 25.1
len(temperatures)    # how many: 5
max(temperatures)    # biggest: 25.1
```

#### Dictionaries
```python
room = {"name": "Classroom 1", "temperature": 21.5, "people": 28}
room["name"]         # "Classroom 1"
```
- key -> value pairs, like a property set on a BIM object.
- A **list of dictionaries** = one dictionary per room. This is how the twin stores building data.

#### Loops and decisions
```python
for room in rooms:
    if room["temperature"] > 23:
        print(room["name"], "is too warm")
    elif room["temperature"] < 20:
        print(room["name"], "is too cold")
    else:
        print(room["name"], "is OK")
```
- `for` repeats an action for every item.
- `if` / `elif` (else if) / `else` make decisions.
- **Rules:** the line before a block ends with `:`, and lines inside the block are indented 4 spaces.

#### Functions
```python
def convert_to_fahrenheit(celsius):
    return (celsius * 9 / 5) + 32
```
- A named recipe: write once, use many times. Inputs are called parameters.
- `return` hands the result back so code can keep using it. `print` only shows it on screen.
- If a rule changes (23 °C becomes 25 °C), I change it in one place.
- I tested it with 0 -> 32 and 100 -> 212: known answers. That is **testing**.
- A **docstring** (`"""..."""` under `def`) describes what the function does.

#### Code style
- Functions go together at the top of the file, then data, then the code that uses them.
- Two blank lines before each `def` (PEP 8, Python's official style guide).
- `#` starts a comment, a note for humans that Python skips.
- **Ruff** fixes style automatically:
  - `uv run ruff format src` fixes layout
  - `uv run ruff check src` finds likely mistakes
- After any change, re-run the code to prove nothing broke.

#### Reading a CSV file
```python
import csv

with open("data/rooms.csv") as file:
    for row in csv.DictReader(file):
        print(row)
```
- CSV = a plain-text table. The first line is the header (column names).
- `import` switches on one of Python's built-in tools.
- `with open(...)` opens the file and closes it automatically.
- `csv.DictReader` turns each row into a dictionary using the header as keys.
- **Trap:** everything in a CSV comes in as **text**. As text, `"9.5"` counts as bigger than `"25.4"`, which gives a wrong answer with no error. Convert with `float()` first.
- Keep data and code in separate files.

---

### 4. What I built

**`data/rooms.csv`:** the first five rooms of the campus (room_id, name, building, temperature_c, occupancy).

**`src/hello.py`:** reads the CSV, converts temperatures to numbers, and finds the warmest and coldest rooms with the "king of the hill" method.

```
uv run python src/hello.py
Warmest room: Staff Room (B3-301) at 25.4 C
Coldest room: Library (B2-202) at 19.6 C
```
I wrote `find_coldest` myself by copying `find_warmest` and flipping `>` to `<`.

**Commits:**
| ID | Message |
|---|---|
| `0d54928` | Set up project with uv and folder layout |
| `90475b8` | Add gitignore file |
| `90a829a` | Add warmest room script, sample room data, Ruff and README |

---

### 5. What broke and how I fixed it

| Problem | Cause | Fix | Lesson |
|---|---|---|---|
| `uv python list` showed "Application Control policy" warnings (error 4551) | Smart App Control blocked two shortcut files | Nothing needed: uv uses the real Python | Read warnings calmly. Not every warning needs action |
| Terminal opened in `C:\WINDOWS\System32` | It was running as Administrator | Opened a normal terminal | Don't work as admin |
| `docker run hello-world` failed: "failed to connect to the docker API" | Docker Desktop (the engine) wasn't running | Opened Docker Desktop | The `docker` command is only a messenger to the engine |
| Docker Desktop: "WSL not installed" | Windows had no WSL 2 | `wsl --install --no-distribution` in an admin terminal, then restarted | Docker on Windows needs WSL 2 and CPU virtualization |
| `uv init` named the project `saija` | A new terminal starts in the home folder, so I ran it in the wrong place | Listed items created in the last hour, deleted only those, redid it in the project folder | Read the prompt before pressing Enter. Look before deleting |
| `git config user.email` still showed my Gmail | Pasted the command onto a line that still had `git status` on it | Pressed Esc to clear the line, then pasted again | Clear the line before pasting |
| GitHub page looked empty | I hadn't pushed yet | Ran `git add`, `git commit`, `git push` | Commit saves locally. Push sends to GitHub |
| New File asked where to save | Used File > New File | Used `New-Item filename` in the terminal | Create files from the terminal or the Explorer's New File icon |
| Output came from the wrong script | Ran `practice.py` instead of `hello.py` | Typed the exact command for `hello.py` | When output is unexpected, first check what I actually ran |

---

### 6. Command cheat sheet

```
# Terminal (PowerShell)
cd C:\Users\saija\projects\mini-connected-estate   # go to the project
mkdir data, tests                                   # make folders
New-Item src\hello.py                               # make an empty file
code .                                              # open this folder in VS Code
code src\hello.py                                   # open one file

# uv
uv python install 3.12
uv init --python 3.12
uv run python src/hello.py
uv add --dev ruff
uv run ruff format src
uv run ruff check src

# Git
git status
git add .
git commit -m "Clear message about what changed"
git push
git remote -v
git config --global user.name "Name"
git config --global user.email "noreply address"

# Docker and WSL
docker run hello-world
wsl --status
```

---


## Module 1: Build the campus and its messy data

**Date:** 23 Nov 2026
**Goal:** create a realistic fake school campus (3 buildings) and the messy data its four systems would produce: BIM model, BMS sensor readings, CAFM repair jobs and compliance documents.
**Result:** done. All four raw data sources plus a private answer key are in `data/`, generated by scripts in `src/`.

---

### 1. Concepts I learned

#### The four places a building's data lives
| Source | What it is | Our file(s) |
|---|---|---|
| **BIM / IFC** | 3D model of the building with information attached to every object. IFC is the free, open file format for it (like PDF for documents) | `data/raw/ifc/campus.ifc` |
| **BMS** (Building Management System) | Runs heating and ventilation. Sensors record a reading every 15 minutes | `data/raw/bms/bms_export_block_a/b/c.csv` |
| **CAFM** (Computer-Aided Facilities Management) | The maintenance team's job log. Each repair job is a **work order** | `data/raw/cafm/work_orders.csv` |
| **Compliance documents** | Legal safety certificates with expiry dates | `data/raw/docs/*.pdf` (24 PDFs) |

#### The IFC family tree
- Project > **Site** > **Building** > **Storey** (floor) > **Space** (room) > **equipment**.
- Every object has an official IFC **class**: `IfcBuilding`, `IfcBuildingStorey`, `IfcSpace`, `IfcBoiler`, `IfcUnitaryEquipment` (air handler), etc. These names are the same in every BIM tool, which is why IFC is the "common language".
- An IFC file is just **text**. Each line is one object: `#46=IFCSPACE('29ZHLV...',$,'B1-101',...,'Classroom 1',...)`. `#46` is the line number, other lines point to it.
- **GlobalId** (`'29ZHLV...'`): a unique code for every object. IfcOpenShell makes a new random one every time the model is rebuilt, so **never use GlobalIds to link data between systems**. Use names/tags like `B1-101` and `AHU-02`.
- Revit can open IFC (File > Open > IFC), but I don't need Revit: Python can read and draw the model.

#### The ID problem (the heart of the project)
The same machine has a different name in every system:

| System | Name for the same air handler |
|---|---|
| BIM model | `AHU-02` |
| BMS | `B1_AHU2` |
| CAFM | `Air Handler 2 Blk A`, `AHU2 Blk A`, `Air handling unit no.2 (Block A)` |
| Documents | `Air Handling Units AHU/A/01 & AHU/A/02` in `O&M_AHU_1_2.pdf` |

Rooms too: `B1-101` (BIM) = `BLKA_GF_CLS01` (BMS) = `Classroom 1` / `Rm 101` / `Class 1 Blk A` (CAFM). A human can guess they match. A computer can't, until we teach it (Module 2).

#### Time series and synthetic data
- **Time series:** a list of readings, each with a time stamp. 6 months x 96 readings a day = about 17,600 rows per sensor.
- **Synthetic data:** data generated by code that behaves like real data. Companies use it to test systems before real data arrives.
- Built in layers: calendar (school days, weekends, holidays) > weather (seasons, day/night) > heating schedule > people > random noise.
- **CO2:** outdoor air is about 420 ppm. People breathe out CO2, so a full classroom climbs above 1,000 ppm, which makes people sleepy.
- **Fixed seed** (`seed=42`): makes the "random" numbers the same every run, on any computer. This is **reproducibility**. (Faker's choices can still differ slightly between computers.)

#### Ground truth (the answer key)
- Like a teacher's marking scheme: the known right answers, written before the test.
- Module 2's matching code must **not** read it. We only use it at the end to score ourselves (target: 95%+).

#### Raw data
- Raw = exactly as it arrives from each system. Never edit raw files by hand; make cleaned copies later.

#### Compliance certificates
| Certificate | Valid for |
|---|---|
| Fire alarm service | 6 months |
| LOLER lift inspection | 6 months |
| Gas safety (boilers) | 12 months |
| Asbestos survey, fire risk assessment | 12 months |
| Legionella risk assessment | 24 months |
| EICR (electrical safety) | 5 years |
| O&M manuals | never expire |

#### New Python ideas
- **Library:** code someone else wrote that we borrow. Installed with `uv add` (also records it in `pyproject.toml`).
- **Variable:** a labelled box holding something (`model = ...`).
- **Function:** a reusable recipe (`def children(parent, ifc_class): ...`).
- **List** `[]` and **append**: an empty basket, then drop things in.
- **Loops inside loops:** building > storey > room > equipment, like opening boxes inside boxes. **Indentation shows what's inside what.**
- **DataFrame** (pandas): an Excel sheet inside Python.
- **x-axis ticks:** major ticks (day names) and minor ticks (06:00, 12:00, 18:00) with `matplotlib.dates`.
- `# fmt: off` / `# fmt: on`: tells Ruff not to rearrange a table.

#### Libraries used
| Library | Job |
|---|---|
| ifcopenshell | Read and write IFC (BIM) files |
| pandas | Tables of data |
| numpy | Fast maths on big lists of numbers |
| faker | Realistic fake names, dates, companies |
| matplotlib | Charts (and a simple 3D view) |
| reportlab | Create PDF files |

---

### 2. The campus: Greenfield Academy

| Building | Storeys | Rooms |
|---|---|---|
| B1 Block A - Teaching | Ground, Floor 1 | B1-101 to B1-107 (classrooms, Main Hall, IT Suite, Plant Room) |
| B2 Block B - Science and Library | Ground, Floor 1 | B2-201 to B2-206 (Science Lab, Library, Prep, Art, Music, Plant Room) |
| B3 Block C - Admin and Staff | Ground | B3-301 to B3-305 (Staff Room, Reception, Head Office, Canteen, Plant Room) |

**20 assets:** 4 air handlers (AHU-01..04), 3 boilers (BLR-01..03), 2 hot water calorifiers (CAL-01..02), 3 distribution boards (DB-01..03), 3 fire alarm panels (FAP-01..03), 3 electricity meters (MTR-01..03), solar array (PV-01), lift (LIFT-01).

---

### 3. What I built

| Script | What it makes | Check |
|---|---|---|
| `src/build_campus.py` | `data/raw/ifc/campus.ifc` | "18 rooms and 20 pieces of equipment" |
| `src/explore_campus.py` | Prints the family tree and counts | 3 buildings, 5 storeys, 18 rooms, 20 equipment |
| `src/view_campus.py` | 3D picture `reports/campus_3d.png` (drag to rotate) | Saw 3 blocks, slabs, red equipment boxes |
| `src/simulate_sensors.py` | 3 BMS CSVs, 6 months, every 15 min | 17,689 / 17,472 / 17,664 rows |
| `src/plot_week.py` | `reports/classroom1_week.png` | 5 weekday "hills", flat weekend, cold Monday morning, gaps where readings are missing |
| `src/make_work_orders.py` | `data/raw/cafm/work_orders.csv` | 308 jobs |
| `src/make_documents.py` | 24 PDFs in `data/raw/docs/` | 9 already expired |
| `src/make_answer_key.py` | `data/answer_key/answer_key.csv` | 43 rows |

#### The mess I created on purpose
- **BMS:** its own room/asset names; ~0.5% readings missing; a few `-999` glitch values; Block B has a 2-day network outage (rows missing); Block A has 25 duplicate rows; Block C writes dates as day/month/year.
- **CAFM:** 2-3 different typed names per asset; messy room names; mixed UK and US dates (`03/01/2026` = 3 Jan or 1 Mar?); some costs with `£`; random CAPITALS and extra spaces; 5 duplicate jobs.
- **Documents:** shared-drive file names like `scan0043.pdf`, `EICR DB2 final v2.pdf`; each certificate names its equipment its own way ("Admin Block fire panel" = FAP-03).

#### The 2 hidden faults (to find in Module 4)
1. **Library (B2-202):** heating valve stuck open 9-29 March 2026. Room 5 C too hot, day and night. Staff complain 3 times in the CAFM.
2. **Science Lab (B2-201):** CO2 sensor frozen at 612 ppm from 12 May 2026 10:00.

---

### 4. What broke and how I fixed it

| Problem | Cause | Fix | Lesson |
|---|---|---|---|
| Thought re-running gives an identical IFC file | GlobalIds are random each run | Link data by names/tags, not GlobalIds | Check assumptions against the real output |
| No Revit | Assumed every BIM learner has it | Drew the model in Python with matplotlib | Free tools can do the job |
| `view_campus.py`: "An Application Control policy has blocked this file" | Smart App Control blocked IfcOpenShell's 3D engine (an unsigned .dll) | Read each box's outline, height and position from the IFC and drew the faces myself | Don't turn Smart App Control off (can't turn it back on without reinstalling). Work around it |
| `git add` warned "LF will be replaced by CRLF" | Windows and Linux end lines differently | Nothing: Git converts automatically | Read warnings calmly |
| Wanted times on the chart, not just dates | Default axis shows dates only | Added day-name major ticks and 06:00/12:00/18:00 minor ticks | Charts are for people: label them clearly |

---

### 5. Command cheat sheet

```
uv add ifcopenshell pandas numpy faker matplotlib reportlab
mkdir data\raw\ifc, data\raw\bms, data\raw\cafm, data\raw\docs
New-Item src\build_campus.py
code src\build_campus.py
uv run python src/build_campus.py
uv run python src/explore_campus.py
uv run python src/view_campus.py
uv run python src/simulate_sensors.py
uv run python src/plot_week.py
uv run python src/make_work_orders.py
uv run python src/make_documents.py
uv run python src/make_answer_key.py
code reports\classroom1_week.png
explorer data\raw\docs
```


