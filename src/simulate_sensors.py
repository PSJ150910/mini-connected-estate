"""Simulate 6 months of BMS sensor readings (every 15 minutes) for the campus.

Run with:  uv run python src/simulate_sensors.py
Creates:   data/raw/bms/bms_export_block_a.csv  (and block_b, block_c)
"""

import numpy as np
import pandas as pd

rng = np.random.default_rng(seed=42)  # fixed seed = same "random" data every run

# ---------------------------------------------------------------
# 1. TIME: every 15 minutes from 1 March to 31 August 2026
# ---------------------------------------------------------------
times = pd.date_range("2026-03-01 00:00", "2026-08-31 23:45", freq="15min")
hour = (times.hour + times.minute / 60).to_numpy()  # 9.25 means 09:15
day_of_year = times.day_of_year.to_numpy()
is_weekend = times.day_of_week.to_numpy() >= 5  # Saturday = 5, Sunday = 6
is_monday = times.day_of_week.to_numpy() == 0

# School holidays: the school is empty on these days
HOLIDAYS = [
    ("2026-03-30", "2026-04-10"),  # Easter
    ("2026-05-25", "2026-05-29"),  # Half term
    ("2026-07-22", "2026-08-31"),  # Summer
]
is_holiday = np.zeros(len(times), dtype=bool)
for start, end in HOLIDAYS:
    is_holiday |= (times >= start) & (times < pd.Timestamp(end) + pd.Timedelta(days=1))
is_school_day = ~is_weekend & ~is_holiday

# ---------------------------------------------------------------
# 2. WEATHER: outdoor temperature with seasons, day/night and noise
# ---------------------------------------------------------------
season = 12 + 7 * np.sin((day_of_year - 105) / 365 * 2 * np.pi)  # cool March, warm July
daily = 4 * np.sin((hour - 9) / 24 * 2 * np.pi)  # coldest ~3am, warmest ~3pm
weather_noise = np.cumsum(rng.normal(0, 0.05, len(times)))  # slow random wander
weather_noise -= (
    pd.Series(weather_noise).rolling(96 * 7, min_periods=1).mean().to_numpy()
)
outdoor = season + daily + weather_noise
sunshine = np.clip(np.sin((hour - 6) / 14 * np.pi), 0, None)  # 0 at night, 1 at 1pm
cloud = np.clip(rng.normal(0.6, 0.25, len(times) // 96 + 1), 0.1, 1)[
    np.arange(len(times)) // 96
]
sun = sunshine * cloud * (0.6 + 0.4 * np.sin((day_of_year - 80) / 365 * 2 * np.pi))

# ---------------------------------------------------------------
# 3. ROOMS: (room id, building, capacity, BMS point prefix)
#    The BMS uses its OWN names for rooms: this is part of the mess!
# ---------------------------------------------------------------
ROOMS = [
    ("B1-101", "A", 30, "BLKA_GF_CLS01"),
    ("B1-102", "A", 30, "BLKA_GF_CLS02"),
    ("B1-103", "A", 120, "BLKA_GF_HALL"),
    ("B1-105", "A", 30, "BLKA_1F_CLS03"),
    ("B1-106", "A", 30, "BLKA_1F_CLS04"),
    ("B1-107", "A", 25, "BLKA_1F_ICT"),
    ("B2-201", "B", 24, "BLKB_GF_SCI_LAB"),
    ("B2-202", "B", 40, "BLKB_GF_LIBRARY"),
    ("B2-203", "B", 4, "BLKB_GF_PREP"),
    ("B2-204", "B", 28, "BLKB_1F_ART"),
    ("B2-205", "B", 28, "BLKB_1F_MUSIC"),
    ("B3-301", "C", 20, "Block C Staff Rm"),
    ("B3-302", "C", 6, "Block C Reception"),
    ("B3-303", "C", 3, "Block C Head Off"),
    ("B3-304", "C", 80, "Block C Canteen"),
]


def occupancy_profile(capacity, room_id):
    """How many people are in the room at each time step."""
    in_lessons = (
        is_school_day & (hour >= 8.75) & (hour < 15.5) & ~((hour >= 12) & (hour < 13))
    )
    fullness = rng.uniform(0.6, 1.0, len(times))
    if room_id == "B3-304":  # canteen: busy only at lunch
        in_lessons = is_school_day & (hour >= 12) & (hour < 13.5)
    people = np.where(in_lessons, capacity * fullness, 0)
    return np.round(people).astype(int)


def room_temperature(people, capacity):
    """Indoor temperature: heating schedule + people + sun + slow drift."""
    heating_on = is_school_day & (hour >= 6) & (hour < 16)
    setpoint = np.where(heating_on, 21.0, 16.0)
    # Heating is weaker in summer, so rooms follow the outdoor air more
    temp = np.where(outdoor > 16, 0.5 * setpoint + 0.5 * (outdoor + 4), setpoint)
    temp = temp + 2.5 * people / max(capacity, 1) + 2.0 * sun
    # Monday mornings: building is still cold from the weekend
    temp = temp - np.where(is_monday & (hour < 10), 2.0, 0)
    # Smooth it: real rooms warm up and cool down slowly
    temp = pd.Series(temp).ewm(span=8).mean().to_numpy()
    return temp + rng.normal(0, 0.15, len(times))


def room_co2(people, capacity):
    """CO2 in ppm: outdoor air is ~420, people breathe it out."""
    co2 = 420 + 900 * people / max(capacity, 1)
    co2 = pd.Series(co2).ewm(span=6).mean().to_numpy()
    return co2 + rng.normal(0, 15, len(times))


# ---------------------------------------------------------------
# 4. BUILD ONE TABLE PER BUILDING
# ---------------------------------------------------------------
tables = {b: pd.DataFrame({"Timestamp": times}) for b in "ABC"}

for room_id, block, capacity, point in ROOMS:
    people = occupancy_profile(capacity, room_id)
    temp = room_temperature(people, capacity)
    co2 = room_co2(people, capacity)

    # HIDDEN FAULT 1: the Library heating valve sticks open for 3 weeks in March,
    # so the room overheats day AND night, even at weekends.
    if room_id == "B2-202":
        stuck = (times >= "2026-03-09") & (times < "2026-03-30")
        temp = np.where(stuck, temp + 5 + rng.normal(0, 0.3, len(times)), temp)

    # HIDDEN FAULT 2: the Science Lab CO2 sensor freezes on 12 May and keeps
    # reporting the same number for the rest of the data.
    if room_id == "B2-201":
        frozen = times >= "2026-05-12 10:00"
        co2 = np.where(frozen, 612.0, co2)

    tables[block][f"{point}_ZoneTemp"] = temp.round(1)
    tables[block][f"{point}_CO2"] = co2.round(0)
    tables[block][f"{point}_Occ"] = people

# Air handling units: supply air temperature and fan on/off
# (note: the BMS names them B1_AHU1 etc, not AHU-01 like the BIM model)
AHUS = [("A", "B1_AHU1"), ("A", "B1_AHU2"), ("B", "B2_AHU1"), ("C", "B3_AHU1")]
for block, name in AHUS:
    fan_on = is_school_day & (hour >= 6) & (hour < 17)
    supply_temp = np.where(fan_on, 18 + rng.normal(0, 0.4, len(times)), outdoor)
    tables[block][f"{name}_SAT"] = supply_temp.round(1)
    tables[block][f"{name}_FanStatus"] = fan_on.astype(int)

# Electricity meters (kWh used in each 15 minutes) and solar panels
BASE_LOAD = {"A": 6, "B": 5, "C": 3}  # kWh per 15 min when empty
for block in "ABC":
    people_in_block = tables[block].filter(like="_Occ").sum(axis=1).to_numpy()
    kwh = BASE_LOAD[block] + 0.08 * people_in_block + rng.normal(0, 0.4, len(times))
    tables[block][f"MTR_BLK{block}_ELEC_kWh"] = np.clip(kwh, 0, None).round(2)
solar = 12 * sun * rng.uniform(0.9, 1.1, len(times))  # no sun = no solar power
tables["C"]["PV_ROOF_GEN_kWh"] = solar.round(2)

# ---------------------------------------------------------------
# 5. MAKE IT MESSY (like a real BMS export) AND SAVE
# ---------------------------------------------------------------
for block, table in tables.items():
    value_columns = table.columns[1:]
    # About 0.5% of readings are simply missing (sensor did not report)
    blanks = rng.random((len(table), len(value_columns))) < 0.005
    table[value_columns] = table[value_columns].mask(blanks)
    # A few crazy spikes where a sensor glitched
    for column in rng.choice(value_columns, 3, replace=False):
        table.loc[rng.choice(len(table), 2), column] = -999

# Block B lost its network connection for 2 days: those rows don't exist at all
outage = (tables["B"]["Timestamp"] >= "2026-06-15") & (
    tables["B"]["Timestamp"] < "2026-06-17"
)
tables["B"] = tables["B"][~outage]

# The BMS sometimes sends the same row twice
tables["A"] = pd.concat(
    [tables["A"], tables["A"].sample(25, random_state=1)]
).sort_index()

# Block C's BMS is a different brand: it writes dates the UK way (day/month/year)
tables["C"]["Timestamp"] = tables["C"]["Timestamp"].dt.strftime("%d/%m/%Y %H:%M")

names = {"A": "block_a", "B": "block_b", "C": "block_c"}
for block, table in tables.items():
    path = f"data/raw/bms/bms_export_{names[block]}.csv"
    table.to_csv(path, index=False)
    print(f"Saved {path}: {len(table)} rows x {len(table.columns)} columns")
