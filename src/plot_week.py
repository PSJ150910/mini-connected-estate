"""Plot one room's temperature for one week, to check the simulator looks real.

Run with:  uv run python src/plot_week.py
Creates:   reports/classroom1_week.png
"""

from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

data = pd.read_csv("data/raw/bms/bms_export_block_a.csv", parse_dates=["Timestamp"])

# Keep one week only: Monday 2 March to Sunday 8 March 2026
week = data[(data["Timestamp"] >= "2026-03-02") & (data["Timestamp"] < "2026-03-09")]

# Hide the -999 glitch values so they don't wreck the chart
temperature = week["BLKA_GF_CLS01_ZoneTemp"].where(
    week["BLKA_GF_CLS01_ZoneTemp"] > -100
)

plt.figure(figsize=(12, 4))
plt.plot(week["Timestamp"], temperature)
plt.title("Classroom 1 (B1-101) temperature, week of 2 March 2026")
plt.ylabel("Temperature (C)")

# Show the day name under each day, and the time every 6 hours
axis = plt.gca().xaxis
axis.set_major_locator(mdates.DayLocator())
axis.set_major_formatter(mdates.DateFormatter("\n\n%a %d %b"))
axis.set_minor_locator(mdates.HourLocator(byhour=[6, 12, 18]))
axis.set_minor_formatter(mdates.DateFormatter("%H:%M"))
plt.setp(axis.get_minorticklabels(), fontsize=7, rotation=90)
plt.grid(which="minor", alpha=0.1)
plt.xlim(pd.Timestamp("2026-03-02"), pd.Timestamp("2026-03-09"))
plt.grid(alpha=0.3)
plt.tight_layout()

Path("reports").mkdir(exist_ok=True)
plt.savefig("reports/classroom1_week.png", dpi=120)
print("Saved reports/classroom1_week.png")
