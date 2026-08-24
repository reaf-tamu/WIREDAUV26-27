# [Sensor Name] — How To

> **Template instructions (delete this blockquote once filled in):** Copy this file to
> `docs/sensors/<sensor-name>.md`, fill in every section below, and delete any bracketed
> placeholder text. If a section genuinely doesn't apply, keep the heading and write
> "N/A — [why]" rather than deleting it, so future readers know it was considered, not missed.

**Owner(s):** [name(s)]
**Last updated:** [date] by [name]
**Status:** [e.g. Working / Partially integrated / Not yet wired]

---

## 1. Overview
[One paragraph: what is this device, in plain language.]

| | |
|---|---|
| Manufacturer / model | |
| Interface | |
| Datasheet | |
| Product page | |
| Driver repo | |
| Approx. cost | |

## 2. What it does and why we use it
- **Sensing principle:**
- **Raw output:**
- **ROS2 message type:**
- **Where it goes:**
- **What breaks without it:**

## 3. Hardware setup
### Mounting
### Wiring
| Sensor pin | Connects to | Notes |
|---|---|---|
- **Power:**
- **Waterproofing/connectors:**
### Safety notes

## 4. Software setup
### Prerequisites
### Where the code lives
### Install / build
```bash
```
### Key config parameters
| Parameter | Default | What it does |
|---|---|---|

## 5. Running it
```bash
```
### Verify it's working
### Visualizing / debugging

## 6. Calibration
- **Does this sensor need calibration?**
- **Procedure:**
- **How often to redo it:**

## 7. Control loop / PID tuning
- **Which loop(s):**
- **Gains live in:**
- **Tuning method:**

| Date | Tuner | Kp | Ki | Kd | Test conditions | Result / notes |
|---|---|---|---|---|---|---|

**Current known-good gains:**

## 8. Coordinate frames
- **TF frame name:**
- **Parent frame:**
- **Offset:**
- **How measured:**

## 9. Troubleshooting
| Symptom | Likely cause | Fix |
|---|---|---|

## 10. Testing & validation
### Bench test
- [ ]
### Pool test checklist
- [ ]

## 11. Maintenance & known limitations
- **Consumables:**
- **Known limitations:**
- **Failure modes seen so far:**

## 12. Change log
| Date | Author | Change |
|---|---|---|
| | | Initial doc created |

## 13. References
