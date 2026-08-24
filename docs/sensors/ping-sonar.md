# Ping Sonar — How To

**Owner(s):** [assign]
**Last updated:** 2026-08-24 by (pre-filled scaffold, not yet verified with real hardware)
**Status:** Not yet wired — sections below are pre-filled from documentation only, not hands-on testing

> Note: sometimes called "Pinger" informally — avoid that name in docs/slides, since it's
> easily confused with RoboSub's unrelated acoustic pinger-locating task (a different device).

---

## 1. Overview
A single-beam echosounder (Blue Robotics Ping Sonar) — measures distance to whatever's
directly in front of its beam. Mounted facing down, it measures altitude above the pool floor.

| | |
|---|---|
| Manufacturer / model | Blue Robotics Ping Sonar |
| Interface | Serial |
| Datasheet | [add link] |
| Product page | [add link] |
| Driver repo | https://github.com/tasada038/ping_sonar_ros |
| Approx. cost | [add] |

## 2. What it does and why we use it
- **Sensing principle:** sends an acoustic pulse and measures the time it takes to bounce back to calculate distance.
- **Raw output:** distance + a confidence value.
- **ROS2 message type:** [confirm from `ping_sonar_ros`]
- **Where it goes:** altitude reference — NOT our primary depth signal (that's the pressure sensor). Used for altitude hold / obstacle awareness.
- **What breaks without it:** loses altitude-above-floor awareness; depth hold still works via the pressure sensor.

## 3. Hardware setup
### Mounting
Downward-facing, for altitude above the pool floor. [TODO once hardware is in hand.]
### Wiring
| Sensor pin | Connects to | Notes |
|---|---|---|
| TODO | | |
### Safety notes
[TODO]

## 4. Software setup
### Install / build
```bash
cd ~/auv_ws/src
git clone https://github.com/tasada038/ping_sonar_ros.git
cd ~/auv_ws && colcon build --packages-select ping_sonar_ros
```

## 5. Running it
```bash
ros2 launch ping_sonar_ros ping_sonar.launch.py
```
### Verify it's working
```bash
ros2 topic echo /ping1d/range
```

## 6. Calibration
- **Does this sensor need calibration?** [Confirm once hardware is in hand.]

## 9. Troubleshooting
| Symptom | Likely cause | Fix |
|---|---|---|

## 13. References
- Driver repo: https://github.com/tasada038/ping_sonar_ros
