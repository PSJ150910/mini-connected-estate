# Data trust rules: Greenfield Academy twin

Written in plain English first. Each rule becomes one check in `src/quality_checks.py`.

| ID | Dimension | Rule | Why it matters |
|---|---|---|---|
| COMP-01 | Complete | Every sensor sends at least 98% of its readings | Gaps make averages and alarms wrong |
| COMP-02 | Complete | Every completed job has a finish date and a cost | Finance and contract reports need both |
| UNIQ-01 | Unique | No asset is listed twice | Two records = jobs and papers split between them |
| UNIQ-02 | Unique | No job is logged twice within 1 day | Duplicate jobs double the cost and the workload |
| VALID-01 | Valid | Every reading is physically possible (e.g. room 5-40 C, CO2 350-5000 ppm) | A -999 glitch would spoil every chart |
| VALID-02 | Valid | Every job has a proper ID, priority, status, cost and clear dates | Bad dates break "time to fix" reports |
| TIME-01 | Timely | No sensor is silent for more than 2 hours | A silent sensor means nobody is watching that room |
| TIME-02 | Timely | No temperature or CO2 sensor shows the same value for over 6 hours | A frozen sensor looks alive but is lying |
| TIME-03 | Timely | No certificate is past its expiry date | Legal risk: gas, fire, lift and Legionella papers |
| CONS-01 | Consistent | Rooms cool below 20 C at night when the heating is off | If not, the sensor or the heating is wrong |
| CONS-02 | Consistent | Every boiler, calorifier, board, fire panel and lift has a certificate | The asset list and the documents must agree |

**Time we measure against:** sensor data ends on 31 Aug 2026, so sensor rules look inside the export period only. Certificates are checked against today's date, because the legal question is "are we safe right now?"

**Score:** each check gives a pass rate (passed items / checked items x 100). A building's score is the average of its check scores, so every rule counts the same. 90+ = GREEN, 75-90 = AMBER, below 75 = RED.
