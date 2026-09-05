# Blue Robotics Ping Sonar — How To

**Owner(s):** Raquel Susko
**Last updated:** 2026-09-04
**Status:** Working — confirmed data flowing (air-tested only; water test still pending)

---

## 1. Overview

The Ping Sonar is a **single-beam echosounder** — it sends out a short acoustic pulse and measures how long the echo takes to come back, giving a distance measurement to whatever's directly in front of it. On our vehicle, it's mounted facing downward and used as an **altimeter** — telling us how far above the pool floor we are, not how deep we are (see section 2 for why these are different things).

| | |
|---|---|
| Manufacturer / model | Blue Robotics Ping Sonar (exact model — Ping1D vs. Ping2 — not yet confirmed; see section 11) |
| Datasheet / product page | https://bluerobotics.com/store/sonars/echosounders/ping-sonar-r2-rp/ |
| Interface | USB-to-TTL adapter currently; native interface is TTL UART (3.3V logic, 5V tolerant) — direct Jetson GPIO wiring is a possible future change, see `docs/issues/` note below |
| Protocol | Ping Protocol (binary, request/response) |
| Driver repo | Custom — `auv_ping` (this repo). See section 4 for why we don't use Blue Robotics' `ping_sonar_ros` ROS2 wrapper. |

---

## 2. What it does and why we use it

**Sensing principle:** An echosounder emits a brief acoustic pulse and times the return echo. Distance = (speed of sound × time elapsed) / 2. This only works accurately when the assumed speed of sound matches the actual medium — a major reason air-testing this sensor gives unreliable results (see section 9).

**Altitude, not depth — these are genuinely different measurements:**
- **Depth** = how far below the *surface* you are (comes from the pressure sensor, feeds the EKF).
- **Altitude** = how far above the *floor* you are, right now, wherever that floor happens to be (comes from this sonar).

**Altitude is never fused into the EKF.** Doing so would require the EKF to also know the true depth of the pool floor at your exact position — a mapping problem we don't need to solve for a flat competition pool. Instead, altitude is read directly by `auv_control`'s `attitude_control_node.py` and used only when `Setpoint.use_altitude_hold` is set — it drives the same vertical thrusters as depth hold, but the two are never active at the same time (see `attitude_control_node.py`'s docstring). See `docs/concepts/kalman-filter.md` for more on what does and doesn't get fused into the EKF.

**Raw output:**
- Distance, in millimeters (converted to meters in our driver — `sensor_msgs/Range` requires meters)
- Confidence, 0-100% — the sensor's own built-in signal-quality indicator for each reading

**ROS2 message types:**
- `sensor_msgs/Range` on `/ping1d/range` — only published for readings that pass the confidence filter (see section 4)
- `std_msgs/Float32` on `/ping1d/confidence` — published for *every* reading, regardless of whether it passed the filter, so raw signal quality is always visible for debugging

**Where it goes:** Subscribed to directly by `auv_control`'s `attitude_control_node.py`, only when altitude-hold mode is active. Never touches `auv_localization`'s EKF.

**What breaks without it:** Altitude-hold mode has no input and can't function. Depth-hold (via the pressure sensor, once wired in) is entirely unaffected — they're independent.

---

## 3. Hardware setup

### Mounting

Mounted facing downward, toward the pool floor. [Photo — TODO]

### Wiring

Currently connected via a **USB-to-TTL adapter**, appearing as a `/dev/ttyUSB*` device — not because the sensor speaks USB natively, but because that's the simplest way to get it talking to the Jetson right now.

| Sensor wire | Adapter pin | Notes |
|---|---|---|
| Black (GND) | GND | Straight across, not crossed — ground is a shared reference, not directional |
| Red (Vin) | PWR | Peak draw (900mA) can exceed what a USB-bus-powered adapter reliably supplies; power from the vehicle's actual power rail instead |
| White (TX, sensor output) | Adapter's **RX** pin | TX↔RX crossed — see `docs/concepts/` note on UART wiring if this is confusing |
| Green (RX, sensor input) | Adapter's **TX** pin | Crossed, same reasoning |

**Native interface, for future reference:** The sensor is natively TTL UART at 3.3V logic (5V tolerant) — electrically compatible with the Jetson's GPIO header UART pins directly, no level shifter needed. We're using a USB adapter for now rather than direct GPIO wiring, mainly to avoid the Jetson header pinmux configuration work and keep the sensor easy to move between test setups. Worth revisiting once the team's USB-hub/port situation (see `docs/issues/usb-hub-power.md`) is finalized — direct GPIO wiring would free up a USB port.

### Safety notes

- Confirm TX/RX are crossed (sensor TX → adapter RX, and vice versa) before powering on — reversed wiring won't damage anything, but nothing will communicate.
- Verified strand quality before final termination — corroded/water-damaged wire strands (dull, discolored, or pulling apart rather than cutting cleanly when stripped) should be cut back to clean wire before connecting, not just powered through.

---

## 4. Software setup

### Why we use a custom driver instead of `ping_sonar_ros`

Blue Robotics' own ROS2 wrapper, `ping_sonar_ros`, brought in more than we needed: a git submodule (Blue Robotics' `ping-python` library, vendored rather than pip-installed) that required manual `git submodule update --init --recursive`, plus a self-referential import inside that submodule requiring a manual `PYTHONPATH` fix to even load, plus a bundled RViz launch configuration pulling in an unrelated plugin dependency (`jsk_rviz_plugin`).

Since Blue Robotics also publishes their `ping-python` library directly on PyPI as **`bluerobotics-ping`** — a normal, `pip`-installable package, not a vendored submodule — we skip their ROS2 wrapper and just call that library's already-written, already-tested functions ourselves from a small custom node. This is a smaller task than it might sound: we're not reimplementing the Ping Protocol's binary message parsing (unlike the VN-100's ASCII rewrite, which really was that kind of task) — just wrapping an existing high-level function call in a ROS2 publisher.

### Where the code lives

- Package path: `auv_ping/` (this repo)
- Node: `auv_ping/auv_ping/ping_node.py`
- Launch file: `auv_ping/launch/ping.launch.py`

### Install / build

```bash
pip3 install bluerobotics-ping
cd ~/auv_ws
colcon build --packages-select auv_ping
```

### Key config parameters

Set as launch parameters in `auv_ping/launch/ping.launch.py`:

| Parameter | Default | What it does |
|---|---|---|
| `port` | `/dev/ping1d` | Serial device path (stable, udev-locked name — see section 8) |
| `baud` | `115200` | Serial baud rate |
| `frame_id` | `ping1d` | TF frame this sensor's data is stamped with |
| `rate_hz` | `10.0` | How often to request a new reading — this is a request/response protocol, not a continuous stream, so this directly sets the actual data rate (unlike the VN-100's polling loop, which polls much faster than data actually arrives) |
| `min_confidence` | `50` | Readings below this confidence (0-100) are dropped rather than published on `/ping1d/range`. **Currently an untuned guess — see section 6.** |
| `min_range_m`, `max_range_m`, `field_of_view_rad` | `0.5`, `30.0`, `0.5236` | **Unverified placeholders** — see section 11, pending confirming exactly which Ping model this is |

---

## 5. Running it

```bash
ros2 launch auv_ping ping.launch.py
```

### Verify it's working

```bash
ros2 topic hz /ping1d/range
```
Expected: a steady rate near `10.0` (matching `rate_hz`). Note this will be **lower** than 10Hz if confidence filtering is dropping a meaningful fraction of readings — that's expected behavior, not a bug, and is itself useful information about signal quality in the current test environment.

```bash
ros2 topic echo /ping1d/confidence
```
Watch this alongside `/ping1d/range` — every reading shows up here, filtered or not, so it's the place to look when trying to understand *why* the range topic seems slow or sparse.

---

## 6. Calibration

- **Confidence threshold (`min_confidence`) is not yet tuned.** Currently set to `50` as a reasonable starting guess, not a value grounded in this sensor's real-world behavior. Air-testing showed occasional readings in the 40s, which got correctly filtered — but air is a poor acoustic environment for this sensor (see section 9), so this doesn't tell us what a *good* underwater reading's confidence actually looks like. **Needs revisiting after a real water test:** check what confidence a known-good, known-distance underwater reading reports, and set the threshold based on that, not a guess.
- **Speed of sound** — Blue Robotics' library exposes a `set_speed_of_sound()` call (default ~1500 m/s, roughly right for fresh water). Not yet explicitly configured in `ping_node.py` — currently relying on the sensor's own default. Worth confirming this default is being used correctly, and setting it explicitly rather than relying on an assumed default, once doing real underwater accuracy testing.

---

## 7. Control loop / PID tuning

- **Which loop(s) does this sensor feed:** Altitude-hold (vertical thrusters), only when `Setpoint.use_altitude_hold` is true. Never depth-hold, never any other axis.
- **Gains live in:** `auv_control/config/pid_gains.yaml`, under `altitude_kp`/`altitude_ki`/`altitude_kd`.
- **Tuning method used:** N/A yet — gains are placeholder `0.0`, and the allocator's vertical-thruster mixing (currently just "all four move together," see `docs/sensors/vn100.md`-adjacent notes in `auv_control`) doesn't yet distinguish altitude-hold from depth-hold at the actuation level; the *setpoint* logic distinguishes them, but tuning real gains should wait until there's real underwater sonar data to tune against.

**Tuning log:**

| Date | Tuner | Kp | Ki | Kd | Test conditions | Result / notes |
|---|---|---|---|---|---|---|
| | | | | | | |

---

## 8. Coordinate frames

- **TF frame name:** `ping1d`
- **Parent frame:** Not yet given a static transform (unlike the VN-100). Since altitude never feeds the EKF, this hasn't been a blocking issue — but if the sensor is ever mounted at a meaningful angle (not straight down) or offset from `base_link`, a static transform should be added the same way it was for the VN-100, so downstream code isn't silently assuming a mounting position that isn't true.

---

## 9. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `Failed to initialize Ping Sonar` at launch | Sensor not powered/connected, or wrong port | Check physical connection; confirm `/dev/ping1d` resolves (`ls -l /dev/ping1d`) |
| `ros2 pkg list` doesn't show `auv_ping` even though `colcon build` reports success with no errors | A subtle, never-fully-diagnosed issue with a hand-created `setup.py`/`package.xml` prevented one specific install hook file (`hook/ament_prefix_path.sh`) from being generated, even though the build itself reported success | Compare `ls install/auv_ping/share/auv_ping/hook/` against a known-working package's equivalent folder — if `ament_prefix_path.sh` is missing, recreate `setup.py`/`setup.cfg`/`package.xml` from a working package's template rather than continuing to debug the original files |
| Readings vary a lot (±0.1m+) even when the sensor is held completely still | **Likely just testing in air, not water.** This sensor is acoustically designed for water — speed of sound differs by ~4x between air and water, air testing often produces poor transducer coupling, and hard surfaces nearby cause multiple overlapping echoes. | Confirm real accuracy/stability with a water test, not an air test. Air testing is fine for confirming "is data flowing at all," not for judging real precision. |
| `/ping1d/range` publishes much slower than `rate_hz` | Confidence filtering is dropping a meaningful fraction of readings | Check `/ping1d/confidence` to see actual values; if this happens during a legitimate water test (not just air-testing noise), the threshold or target surface may need adjustment |
| `Serial read failed: device reports readiness to read but returned no data` | Port contention — usually an orphaned node from a previous launch attempt still holding `/dev/ping1d` open | `sudo fuser -v /dev/ping1d`, kill any extra PIDs, relaunch (same fix pattern as the VN-100 — see `docs/sensors/vn100.md`) |

---

## 10. Testing & validation

### Bench test (air) — confirms plumbing only, not accuracy
- [x] Confirm `ros2 topic hz /ping1d/range` shows a steady rate
- [x] Confirm the value trends in the correct direction when moved closer/farther from a surface
- [ ] Do **not** treat air-test jitter as a real accuracy problem — see Troubleshooting

### Water test (still pending) — the real validation
- [ ] Point sensor at a known, measured distance from a hard, flat, perpendicular surface underwater
- [ ] Compare reported `range` against the physically measured distance at 2-3 different distances
- [ ] Record what `confidence` looks like for known-good readings — use this to set a real `min_confidence` threshold (see section 6)
- [ ] Confirm `range` stability (variation while stationary) is small relative to the sensor's spec'd resolution (~0.5% of range), not the 0.1m+ swings seen in air

---

## 11. Maintenance & known limitations

- **Exact model (Ping1D vs. Ping2) not yet confirmed.** Both share the same `Ping1D` software class and (as far as we could determine) the same `device_type` protocol field, so this can't be resolved from code alone with full confidence. Best path: Blue Robotics' **Ping Viewer** desktop app displays the exact product name directly. Until confirmed, `min_range_m`/`max_range_m`/`field_of_view_rad` in the launch file are approximate general-family values, not this specific unit's real datasheet numbers.
- **Not yet mounted/tested underwater** — everything confirmed so far is bench/air-only.
- **No static TF transform yet** — see section 8.
- **Speed-of-sound setting not explicitly configured** — see section 6.
- **Currently wired via USB adapter, not the Jetson's native UART pins** — a possible future change tied to the team's broader USB port/hub planning (`docs/issues/usb-hub-power.md`).

---

## 12. Change log

| Date | Author | Change |
|---|---|---|
| 2026-09-04 | (this session) | Initial doc written — `auv_ping` driver working (air-tested), confidence filtering added, `ping_sonar_ros` retired |

---

## 13. References

- Product page / datasheet: https://bluerobotics.com/store/sonars/echosounders/ping-sonar-r2-rp/ — the "R2" in this URL may itself be a useful clue toward resolving the Ping1D vs. Ping2 question in section 11; worth checking this page's specs against Ping Viewer's reported model before assuming which one this confirms.
- Ping Protocol docs: https://docs.bluerobotics.com/ping-protocol/
- `bluerobotics-ping` PyPI package: https://pypi.org/project/bluerobotics-ping/
- Related club docs: `docs/concepts/kalman-filter.md` (why altitude isn't fused into the EKF), `docs/sensors/vn100.md` (same custom-driver-over-vendor-wrapper pattern, same udev rule approach), `docs/issues/usb-hub-power.md`
