# DVL — How To

**Owner(s):** [assign]
**Last updated:** 2026-08-24 by (pre-filled scaffold, not yet verified with real hardware)
**Status:** Not yet wired — this is our longer-term priority sensor; sections below are pre-filled from documentation only

---

## 1. Overview
A Doppler Velocity Log — measures the vehicle's velocity relative to the seafloor,
enabling real dead-reckoning position tracking (something the other sensors alone can't provide).

| | |
|---|---|
| Manufacturer / model | [fill in exact model] |
| Interface | [fill in] |
| Datasheet | [add link] |
| Product page | [add link] |
| Driver repo | None found — likely needs vendor SDK integration or a custom node |
| Approx. cost | [add] |

## 2. What it does and why we use it
- **Sensing principle:** bounces acoustic beams off the pool floor and measures the Doppler shift to calculate velocity.
- **Raw output:** 3-axis velocity, often altitude as well.
- **ROS2 message type:** likely `geometry_msgs/TwistWithCovarianceStamped`.
- **Where it goes:** primary velocity input to `auv_localization`'s EKF, enabling real position (dead-reckoning) tracking; also feeds surge/sway PID loops in `auv_control` once wired.
- **What breaks without it:** no reliable position tracking between tasks, and no closed-loop surge/sway control — these currently have to run open-loop or rely on vision-based servoing instead.

## 3. Hardware setup
### Mounting
Downward-facing, needs an unobstructed view of the pool floor. [TODO once hardware is in hand.]
### Wiring
| Sensor pin | Connects to | Notes |
|---|---|---|
| TODO | | Not yet integrated into our electrical circuit — see project status |
### Safety notes
[TODO]

## 4. Software setup
### Prerequisites
No existing ROS2 package found — plan to write a custom driver, likely using a vendor-provided SDK/protocol library. Confirm once model is finalized.

## 5. Running it
TBD — driver not yet written.

## 6. Calibration
[TODO once hardware is in hand — DVLs often need beam alignment/verification against known distances.]

## 7. Control loop / PID tuning
- **Which loop(s):** surge (forward/back velocity), sway (left/right velocity), and enables real position hold
- **Gains live in:** TBD, `auv_control` config (not yet written)

## 9. Troubleshooting
| Symptom | Likely cause | Fix |
|---|---|---|

## 13. References
[Add datasheet and vendor SDK links once exact model is confirmed.]
