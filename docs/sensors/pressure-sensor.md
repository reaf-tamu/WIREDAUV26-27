# Blue Robotics Bar02 Pressure Sensor — How To

**Owner(s):** [assign]
**Last updated:** 2026-09-05
**Status:** Package written, not yet bench-tested against real hardware

---

## 1. Overview

The Bar02 measures water pressure and converts it into **depth** — how far below the surface the vehicle is. This is a genuinely different measurement from the Ping Sonar's altitude (how far above the *floor*) — see `docs/sensors/ping-sonar.md` section 2 and `docs/concepts/kalman-filter.md` for why these are kept separate and only depth ever feeds the EKF.

| | |
|---|---|
| Manufacturer / model | Blue Robotics Bar02 (chip: MS5837-02BA) |
| Product page | https://bluerobotics.com/store/sensors-cameras/sensors/bar-depth-pressure-sensor/ |
| Interface | **I2C** — not USB/serial like every other sensor in this repo so far |
| Default I2C address | `0x76` |
| Range | Up to 2 bar (~10m depth), 0.16mm resolution |
| Driver repo | Custom — `auv_pressure` (this repo), wrapping Blue Robotics' official `ms5837-python` library |
| Approx. cost | [add] |

---

## 2. What it does and why we use it

**Sensing principle:** the MS5837-02BA chip measures absolute pressure and temperature, then applies factory-calibrated compensation coefficients to convert that into an accurate pressure reading. That calibration math is proprietary to the chip's specific manufacturing batch (each unit's exact coefficients are baked in at the factory) — this is exactly the kind of precision-critical conversion we do **not** reimplement ourselves; see section 4 for why.

**Depth vs. pressure vs. altitude — worth being precise about:**
- **Pressure** is the raw physical measurement (in Pa/mbar/etc).
- **Depth** is pressure converted into "meters below the surface," using the local fluid's density (freshwater vs. saltwater — a pool is freshwater, density ≈ 997 kg/m³, which is this sensor's library default).
- **Altitude** (from the Ping Sonar) is a completely different, unrelated measurement — see `docs/sensors/ping-sonar.md`.

**ROS2 message types:**
- `sensor_msgs/FluidPressure` on `/pressure/fluid_pressure` — the raw measurement
- `geometry_msgs/PoseWithCovarianceStamped` on `/localization/depth_pose` — depth only (`position.z`), formatted specifically to match the `pose0` placeholder already stubbed (commented out) in `auv_localization/config/ekf.yaml`

**Where it goes:** once wired in, feeds `auv_localization`'s EKF as the `pose0` source, giving the vehicle its actual depth estimate in `/odometry/filtered`. **Not yet connected** — see section 9/11.

**What breaks without it:** the EKF's z-position is currently a meaningless placeholder (we deliberately excluded raw accelerometer integration — see `docs/concepts/kalman-filter.md` — so there's genuinely no depth estimate at all right now). Depth-hold in `auv_control` cannot function until this is wired in.

---

## 3. Hardware setup

### Mounting

[Photo / mounting details — TODO]

### Wiring

**This sensor uses I2C, not UART/serial** — a real, categorical difference from every other sensor driver in this repo so far (VN-100, Ping Sonar). Different pins, different bus, different Linux subsystem.

| Sensor wire | Connects to |
|---|---|
| GND | Ground |
| V+ | Power (per datasheet voltage range) |
| SDA | Jetson I2C data pin |
| SCL | Jetson I2C clock pin |

Currently wired directly to the Jetson's I2C header pins (not via a USB adapter) — see `docs/issues/usb-hub-power.md` for the team's broader USB-vs-direct-wiring discussion; this sensor was always planned to go direct since it never had a USB variant to begin with.

### Safety notes

Standard I2C wiring care — confirm SDA/SCL aren't swapped before powering on (unlike UART, there's no simple "nothing communicates" fallback if reversed; double-check against the sensor's own pinout label).

---

## 4. Software setup

### Why we use Blue Robotics' official library directly, not our own calibration math

The MS5837-02BA's pressure/temperature conversion involves manufacturer-calibrated compensation coefficients unique to each sensor. **We deliberately do not reimplement this ourselves** — unlike the VN-100 (where we replaced a misbehaving binary driver with our own simple ASCII parser) or the Ping Sonar (where we called one already-correct library function), a pressure sensor's calibration math is precision-critical in a way that's genuinely risky to hand-transcribe: a single sign or ordering error would silently produce wrong depth readings that *look* plausible.

Blue Robotics publishes their own official library, `ms5837-python`, but it's **not on PyPI** — install it directly from GitHub instead:
```bash
pip3 install git+https://github.com/bluerobotics/ms5837-python.git
```
This sidesteps the git-submodule-inside-our-repo pain we hit with `ping_sonar_ros` (no submodule to forget to initialize, no PYTHONPATH quirks) while still using Blue Robotics' real, tested calibration code rather than our own.

### Where the code lives

- Package path: `auv_pressure/` (this repo)
- Node: `auv_pressure/auv_pressure/pressure_node.py`
- Launch file: `auv_pressure/launch/pressure.launch.py`

### Install / build

```bash
pip3 install git+https://github.com/bluerobotics/ms5837-python.git
sudo apt install i2c-tools
cd ~/auv_ws
colcon build --packages-select auv_pressure
```

### Enable I2C access

```bash
sudo i2cdetect -y 1
```
Look for `76` in the output grid. **If nothing shows up on bus `1`**, the correct I2C bus number for this Jetson model's 40-pin header hasn't been confirmed yet — don't assume `1` is right without checking.

```bash
groups $USER
sudo usermod -aG i2c $USER   # if 'i2c' isn't listed; log out/in after
```

### Key config parameters

Set as launch parameters in `auv_pressure/launch/pressure.launch.py`:

| Parameter | Default | What it does |
|---|---|---|
| `i2c_bus` | `1` | **Unconfirmed** — verify against `i2cdetect` output for this specific Jetson |
| `frame_id` | `pressure_sensor` | TF frame this sensor's data is stamped with |
| `rate_hz` | `10.0` | Polling rate |
| `fluid_density_kg_m3` | `997.0` | Freshwater — correct default for a pool, matches the library's own default |
| `depth_variance` | `0.01` | **Untuned placeholder** — not measured from real sensor noise yet |

---

## 5. Running it

```bash
ros2 launch auv_pressure pressure.launch.py
```

### Verify it's working

```bash
ros2 topic hz /pressure/fluid_pressure
ros2 topic echo /localization/depth_pose
```

**Real validation — not yet done:** submerge the sensor a known distance and confirm the reported depth roughly tracks it. Bench/air testing alone (like we did initially with the Ping Sonar) won't validate this meaningfully, since pressure barely changes with a few centimeters of air.

---

## 6. Calibration

- **Per-unit calibration:** handled entirely inside the MS5837-02BA chip itself and read out via the official library — nothing for us to calibrate here.
- **Fluid density:** already set correctly for freshwater/pool use (997 kg/m³, the library's own default). Would need changing if this vehicle is ever tested in saltwater.
- **`depth_variance`:** placeholder, not yet tuned against real sensor noise — same situation the VN-100's initial covariance values were in.

---

## 7. Control loop / PID tuning

- **Which loop(s) does this sensor feed:** Depth-hold (vertical thrusters), once wired into the EKF. Not usable yet — see section 9.
- **Gains live in:** `auv_control/config/pid_gains.yaml`, `depth_kp`/`depth_ki`/`depth_kd`.
- **Tuning method used:** N/A — blocked on EKF integration (section 11).

**Tuning log:**

| Date | Tuner | Kp | Ki | Kd | Test conditions | Result / notes |
|---|---|---|---|---|---|---|
| | | | | | | |

---

## 8. Coordinate frames

- **TF frame name:** `pressure_sensor`
- **Sign convention:** `position.z` in `/localization/depth_pose` is published as **negative** depth, consistent with the ENU (z-up) convention used elsewhere in this stack (see `docs/concepts/euler-quaternions.md`). **This has not been empirically verified** — it's a documented assumption based on convention, not a confirmed-correct result. Confirm once this is actually feeding the EKF and compare against expected behavior.
- No static mounting transform yet — add one if the sensor is ever mounted somewhere that isn't representative of the vehicle's true depth reference point.

---

## 9. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `i2cdetect` shows nothing at `0x76` | Wrong I2C bus number, wiring issue, or SDA/SCL swapped | Check wiring against the sensor's pinout; try other bus numbers if unsure which is correct for this Jetson's header |
| `Failed to initialize Bar02` in node logs | Sensor not detected — same root causes as above | Confirm `i2cdetect` sees it before debugging the ROS node further |
| Depth readings don't change when submerged | `fluid_density_kg_m3` misconfigured, or genuinely not connected to the real sensor (check `HARDWARE_AVAILABLE` warning in logs) | Confirm `pip3 show ms5837` shows it installed; re-check wiring |
| `ms5837` import fails | Library not installed, or installed in a different Python environment than the one ROS2 is using | Re-run the `pip3 install git+https://...` command; confirm with `python3 -c "import ms5837"` directly |

---

## 10. Testing & validation

### Bench test
- [ ] Confirm `ros2 topic hz /pressure/fluid_pressure` shows a steady rate
- [ ] Confirm `i2cdetect -y 1` (or correct bus) shows `76`

### Water test — not yet done
- [ ] Submerge to a known, measured depth; confirm reported depth roughly matches
- [ ] Repeat at 2-3 depths to confirm it tracks correctly across a range
- [ ] Confirm the `-depth_m` sign convention actually produces the expected direction once wired into the EKF

---

## 11. Maintenance & known limitations

- **Not yet wired into `ekf.yaml`** — the `pose0` block this node was designed to match is still commented out. This is the next real step once bench testing confirms the sensor itself works.
- **I2C bus number (`1`) is unconfirmed** for this specific Jetson model's header.
- **Depth sign convention is a documented assumption**, not empirically verified.
- **`depth_variance` is an untuned placeholder.**
- **No water test performed yet** — everything so far is code-complete but hardware-unverified.

---

## 12. Change log

| Date | Author | Change |
|---|---|---|
| 2026-09-05 | (this session) | Initial doc written — `auv_pressure` driver created using Blue Robotics' official ms5837-python library, not yet bench-tested |

---

## 13. References

- Product page: https://bluerobotics.com/store/sensors-cameras/sensors/bar-depth-pressure-sensor/
- Official library: https://github.com/bluerobotics/ms5837-python
- Related club docs: `docs/concepts/kalman-filter.md` (why depth and altitude are fused differently), `docs/sensors/ping-sonar.md` (the altitude/depth distinction), `docs/sensors/vn100.md` (same custom-driver-over-vendor-wrapper pattern)
