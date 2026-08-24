# Pressure Sensor — How To

**Owner(s):** [assign]
**Last updated:** 2026-08-24 by (pre-filled scaffold, not yet verified with real hardware)
**Status:** Not yet wired — sections below are pre-filled from documentation only, not hands-on testing

---

## 1. Overview
Measures water pressure and converts it to depth — our primary, direct depth
reference (distinct from the Ping Sonar, which measures altitude above the floor,
not depth below the surface).

| | |
|---|---|
| Manufacturer / model | [fill in exact model] |
| Interface | I2C (typical for this sensor class) |
| Datasheet | [add link] |
| Product page | [add link] |
| Driver repo | None found — likely needs a small custom driver node |
| Approx. cost | [add] |

## 2. What it does and why we use it
- **Sensing principle:** measures water pressure and converts it to depth using the hydrostatic equation.
- **Raw output:** depth in meters (often also temperature).
- **ROS2 message type:** likely `sensor_msgs/FluidPressure`, or a plain depth value fed into the EKF as a pose/position input — decide when writing the driver.
- **Where it goes:** primary feedback for the depth PID loop in `auv_control`; also feeds `auv_localization`'s EKF as the z-position input.
- **What breaks without it:** no reliable depth-hold — the vehicle has no direct way to know how deep it is.

## 3. Hardware setup
### Mounting
[TODO once hardware is in hand — needs direct water contact, check for a vent/port design.]
### Wiring
| Sensor pin | Connects to | Notes |
|---|---|---|
| TODO | | |
### Safety notes
[TODO — waterproofing/potting is critical for this sensor specifically.]

## 4. Software setup
### Prerequisites
No existing ROS2 driver found for this sensor class — plan to write a small custom
node reading over I2C. See `docs/architecture-roadmap.md` for where this fits.
### Where the code lives
TBD — likely a new small package, or grouped into `auv_localization` if kept simple.

## 5. Running it
TBD — driver not yet written.

## 6. Calibration
- **Does this sensor need calibration?** Likely a zero-offset calibration at the surface before each use. [Confirm procedure once hardware is in hand.]

## 7. Control loop / PID tuning
- **Which loop(s):** depth
- **Gains live in:** TBD, `auv_control` config (not yet written)

## 9. Troubleshooting
| Symptom | Likely cause | Fix |
|---|---|---|

## 13. References
[Add datasheet and any I2C library references once the exact part is confirmed.]
