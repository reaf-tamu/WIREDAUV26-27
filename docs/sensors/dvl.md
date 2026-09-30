# Teledyne Wayfinder DVL — How To

**Owner(s):** [assign]
**Last updated:** 2026-09-XX
**Status:** Driver validated on Windows/VM with real water data; ROS2 node written, not yet run on the Jetson

---

## 1. Overview

A **DVL (Doppler Velocity Log)** measures the vehicle's velocity relative to the floor (or the water column, if the floor's out of range) by bouncing acoustic pulses off it and measuring the Doppler shift in the return — similar acoustic principle to the Ping Sonar, but measuring *speed*, not *distance*.

**This is the sensor that eventually unblocks surge as a real, closed-loop-controllable axis.** Every other axis (roll/pitch/yaw via the VN-100, depth via the pressure sensor, altitude via the Ping Sonar) has a direct, drift-free measurement. Surge and sway do not — there's no direct x/y position sensor on this vehicle, and a DVL's velocity is what makes dead-reckoning (continuously adding up velocity over time to estimate position) possible at all. See `docs/concepts/kalman-filter.md` and the surge-vs-position discussion in `auv_control`'s docs for why this matters.

| | |
|---|---|
| Manufacturer / model | Teledyne Wayfinder |
| Interface | RS232 (tested via a USB-to-RS232 adapter) |
| Baud rate | 115200 |
| Driver | Teledyne's own official Python SDK (`dvl` package) — vendor download, not on PyPI |
| Driver repo | Custom — `auv_dvl` (this repo), wrapping Teledyne's SDK directly |

---

## 2. What it does and why we use it

**Sensing principle:** 4 acoustic beams, each measuring range and contributing to a combined velocity estimate via Doppler shift — `mean_range` plus `range_beam1`-`range_beam4` give per-beam detail, `vel_x`/`vel_y`/`vel_z` give the combined velocity result.

**What it does NOT give us:** absolute position. Like the Ping Sonar's altitude, a DVL's output has to be integrated (added up over time) to get position, and that process drifts — it's a velocity sensor, not a position sensor. This is why `auv_control`'s surge PID loop is designed around a velocity setpoint, not a position setpoint (see the surge-vs-other-axes discussion already written up for `attitude_control_node.py`/`pid_control_node.py`).

**ROS2 message type:** `nav_msgs/Odometry` on `/dvl/odometry` — only the `twist.twist.linear` (velocity) fields are populated; `pose` is left empty, since this sensor doesn't measure position directly.

**Where it goes:** intended to feed `auv_localization`'s EKF as the `odom0` source (currently commented out in `ekf.yaml`, waiting on this sensor) and `auv_control`'s surge PID. **Not yet connected to either** — see section 11.

**What breaks without it:** surge stays open-loop only — commands go straight to the thrusters with no feedback on whether the vehicle's actually moving at the commanded speed.

---

## 3. Hardware setup

### Wiring

Connected via a **USB-to-RS232 adapter** (not a direct TTL UART connection like the VN-100 or Ping Sonar — RS232 uses different voltage levels, hence the adapter). Tested at **115200 baud**.

### Safety notes

Standard cabling care for the RS232 adapter and connector — nothing sensor-specific beyond that noted yet.

---

## 4. Software setup

### Why we use Teledyne's official driver directly

Same reasoning as the Ping Sonar and pressure sensor: a DVL's internal beam-to-velocity computation is proprietary, precision-critical processing we have no business reimplementing. Teledyne's own Python SDK already does this correctly — confirmed by an early standalone test (see section 10) that connected, read live data, and returned sensible velocity/range values during an actual water test.

### Installing the driver

**This is a vendor download, not a public PyPI or git package** — unlike `bluerobotics-ping` or `ms5837-python`, there's no URL to `pip install` directly from. Download the driver from Teledyne (account/access may be required), then install from that local directory:
```bash
python3 -m pip install pyserial
cd /path/to/downloaded/driver
python3 -m pip install .
```

### Where the code lives

- Package path: `auv_dvl/` (this repo)
- Node: `auv_dvl/auv_dvl/dvl_node.py`
- Launch file: `auv_dvl/launch/dvl.launch.py`
- Original standalone test script + notes: `auv_dvl/read_dvl.py`, `auv_dvl/README.md` — this is where the real water-test validation actually happened; worth reading alongside this doc for the raw test history.

### Build

```bash
cd ~/auv_ws
colcon build --packages-select auv_dvl
```

### Key config parameters

Set as launch parameters in `auv_dvl/launch/dvl.launch.py`:

| Parameter | Default | What it does |
|---|---|---|
| `port` | `/dev/dvl` | Serial device path — **not yet given a real udev rule**, see section 9 |
| `baud` | `115200` | Confirmed correct from the original standalone test |
| `frame_id` | `dvl` | TF frame this sensor's data is stamped with |

---

## 5. Running it

```bash
ros2 launch auv_dvl dvl.launch.py
```

### Verify it's working

```bash
ros2 topic echo /dvl/odometry
```
Expect `twist.twist.linear.x/y/z` to show real, changing values while the vehicle moves — `pose` fields will be empty/zero, which is expected (see section 2).

Node startup logs the DVL's own reported system info (firmware version, frequency, beam angle, etc.) — worth checking against the values from the original standalone test (firmware `1.1.0.4`, 614400.0 Hz, 30.0° beam angle) to confirm it's the same, correctly-functioning unit.

---

## 6. Calibration

Nothing to calibrate on our end — beam-to-velocity conversion is handled entirely inside the DVL/SDK. **Speed of sound** is a configurable setting on the device itself (confirmed `1500.0` in the original test's `system_setup` readout) — worth confirming this matches your actual water conditions (freshwater pool) rather than assuming the factory default is automatically correct.

---

## 7. Control loop / PID tuning

- **Which loop(s) does this sensor feed:** Surge (the velocity-based loop already built into `pid_control_node.py`). Not usable yet — blocked on EKF integration (section 11) and coordinate frame resolution (section 8).
- **Gains live in:** `auv_control/config/pid_gains.yaml`, `surge_kp`/`surge_ki`/`surge_kd`.
- **Tuning method used:** N/A yet.

**Tuning log:**

| Date | Tuner | Kp | Ki | Kd | Test conditions | Result / notes |
|---|---|---|---|---|---|---|
| | | | | | | |

---

## 8. Coordinate frames

- **TF frame name:** `dvl`
- **Status: NOT resolved — this is the biggest open item for this sensor.** `vel_x`/`vel_y`/`vel_z` are currently published exactly as the DVL SDK reports them, in the sensor's own native axis convention. This has not been checked against our ENU convention, the same category of issue the VN-100 had before its mounting transform was worked out (see `docs/sensors/vn100.md` section 8) — but unlike the VN-100, this hasn't been investigated at all yet, not even a first guess.
- **No static mounting transform exists yet.**
- **Before trusting this sensor's data in the EKF or surge PID:** confirm the Wayfinder's actual native reporting convention (check the manual for whether it's FRD/NED-style or something else) and the sensor's real mounting orientation on the vehicle, then build the appropriate transform — the same process already done once for the VN-100.

---

## 9. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `Could not connect to DVL: <error>` | Wrong port, sensor not powered, RS232 adapter issue | Confirm the correct `/dev/ttyUSB*` device (`ls /dev/ttyUSB*`, check `dmesg`), same debugging approach used for the VN-100 |
| Node logs show driver import warning | Teledyne's `dvl` package isn't installed, or installed in a different Python environment than ROS2 is using | Re-run the `pip3 install .` step from the downloaded driver directory; confirm with `python3 -c "import dvl"` |
| Data received but `data.is_valid` is always `False` | Sensor not actually in range of a reflective bottom, or genuine hardware/beam issue | Confirm test conditions match a real validated setup (enough water depth below the sensor for a valid beam return) |
| Port keeps shifting between `/dev/ttyUSB0`/`ttyUSB1` across reboots | No udev rule set up yet for this sensor | Follow `docs/concepts/udev-rules.md` to lock in a stable `/dev/dvl` name, same as done for the VN-100 and Ping Sonar |

---

## 10. Testing & validation

### Standalone driver test (Windows/VM) — confirmed working
- [x] Connected successfully via Teledyne's SDK over a USB-to-RS232 adapter at 115200 baud
- [x] Read system info successfully (firmware 1.1.0.4, 614400.0 Hz, 30.0° beam angle, 1500.0 m/s speed of sound, 60.0m max depth/range)
- [x] **Real water test performed** — live velocity and per-beam range data confirmed while submerged, e.g.:
  ```
  Vx=-0.133 m/s  Vy=0.484 m/s  Vz=-0.030 m/s  Range=1.001 m
  ```
  This confirms the sensor and Teledyne's driver both genuinely work — a real, meaningful validation step already complete, independent of anything ROS2/Jetson-related.

### ROS2/Jetson integration — not yet done
- [ ] Confirm the `auv_dvl` ROS2 node connects and publishes on the actual Jetson (vs. the Windows/VM test environment used so far)
- [ ] Set up a udev rule for a stable port name
- [ ] Resolve the coordinate frame question (section 8) before trusting any published values
- [ ] Wire into `ekf.yaml`'s `odom0` block once the above is confirmed

---

## 11. Maintenance & known limitations

- **Coordinate frame is a fully open question** — see section 8. This is the single most important thing to resolve before this sensor is trustworthy for anything beyond raw debugging.
- **Not yet wired into `ekf.yaml`** — `odom0` remains commented out, waiting on the above.
- **No udev rule yet** — currently relies on a `/dev/dvl` parameter default that doesn't actually resolve to anything stable until a rule is created.
- **Validated hardware/driver combination differs from the deployment environment** — the successful test was on Windows via VMware Fusion; the ROS2 node targets Linux/Jetson directly, which hasn't been exercised yet. The underlying SDK behavior should be the same, but this hasn't been confirmed on the actual target hardware.

---

## 12. Change log

| Date | Author | Change |
|---|---|---|
| 2026-09-XX | (this session) | `auv_dvl` ROS2 package written, wrapping the already-validated Teledyne driver; coordinate frame and EKF integration left open |

---

## 13. References

- Original standalone test script and notes: `auv_dvl/read_dvl.py`, `auv_dvl/README.md`
- Related club docs: `docs/concepts/kalman-filter.md` (why velocity-only sensors still need integration/drift-correction), `docs/sensors/vn100.md` (same coordinate-frame-resolution process this sensor still needs), `docs/concepts/udev-rules.md`

