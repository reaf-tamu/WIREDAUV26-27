# auv_localization

Fuses sensor data into one trustworthy estimate of the vehicle's position, orientation, and velocity — the single source of truth everything else (control, mission logic) reads from.

## What this package is — and isn't

Unlike every other package in this repo (`auv_vn100`, `auv_ping`, `auv_pressure`, `auv_dvl`, `auv_control`), **this package has no custom node code.** We don't write our own Kalman filter — we configure and launch `robot_localization`'s own `ekf_node` directly, the same philosophy as using a sensor manufacturer's own library instead of reimplementing their math. "The code" here really is two files:

| File | Role |
|---|---|
| `config/ekf.yaml` | Which sensors to fuse, which specific fields from each to trust, and the filter's tuning parameters |
| `launch/ekf.launch.py` | Starts `robot_localization`'s `ekf_node`, loaded with `ekf.yaml` |

## What a Kalman filter actually does (briefly)

Every sensor is a little noisy and gives you a different piece of the picture — orientation, depth, velocity, none of it complete on its own. A Kalman filter continuously blends a *prediction* of where the vehicle should be (based on its last known motion) with each new sensor reading as it arrives, weighted by how much it trusts each source. The result is one smooth, continuously-updated estimate that's more reliable than any single sensor alone.

**For the full explanation — the predict/update cycle, why it beats averaging, gimbal lock and why this matters for orientation specifically — see [`docs/concepts/kalman-filter.md`](../docs/concepts/kalman-filter.md).** This README stays focused on how *our* config actually uses it.

## Where this fits in the launch chain

```
auv_bringup/launch/bringup.launch.py
    └── includes auv_localization/launch/ekf.launch.py
            └── starts robot_localization's ekf_node (named "ekf_filter_node"),
                configured by auv_localization/config/ekf.yaml
```

`ekf_node` belongs to `robot_localization`, not to this package — that's why `ros2 node list` shows it as `ekf_filter_node`, not `auv_localization`.

## Running it

As part of the full stack:
```bash
ros2 launch auv_bringup bringup.launch.py
```

Standalone, for isolated testing:
```bash
ros2 launch auv_localization ekf.launch.py
```

**Verify it's producing output:**
```bash
ros2 topic hz /odometry/filtered
ros2 topic echo /odometry/filtered
```

## What's currently fused, and what isn't yet

| Sensor | Topic | Status |
|---|---|---|
| VN-100 (orientation, angular velocity) | `/vectornav/imu` | **Active** |
| Pressure sensor (depth) | `/localization/depth_pose` | Written, **commented out** — sign convention not yet water-verified, see `docs/sensors/pressure-sensor.md` |
| DVL (surge/sway velocity) | `/dvl/odometry` | Written, **commented out** — yaw alignment not yet water-verified, see `docs/sensors/dvl.md` |

**Don't uncomment `pose0`/`odom0` just because the sensor is publishing data.** Both are deliberately held back until their respective physical verification steps confirm the data is actually correct — wiring in unverified data doesn't fail loudly, it just quietly corrupts the fused estimate everything downstream trusts. Once a sensor's water test confirms its sign/alignment, uncomment its block in `ekf.yaml` and the corresponding lines in `bringup.launch.py`.

## How the config actually works — `_config` arrays

Each sensor gets a numbered block (`imu0`, `pose0`, `odom0`, ...) and a matching `..._config` array — 15 `true`/`false` values, one per field the filter could use: position (x,y,z), orientation (roll,pitch,yaw), velocity (x,y,z), angular velocity (roll,pitch,yaw), linear acceleration (x,y,z). Only flip `true` for what that specific sensor actually, reliably measures — e.g. the VN-100 gets orientation/angular velocity/acceleration, never position, because it doesn't measure position at all.

## Tuning `process_noise_covariance`

This is a 15×15 matrix (laid out as 15 rows of 15 values) representing one thing: **how much the filter should expect the true state to drift between updates, with no new sensor data.** Each diagonal entry corresponds to one of those same 15 fields (x, y, z, roll, pitch, yaw, ...) — larger value = "I expect more uncertainty/wander here" = the filter leans more heavily on fresh sensor corrections for that field; smaller value = "I trust my own prediction more" = smoother but slower to react to real changes.

**Current values are starting placeholders, not measured from real sensor noise.** Real tuning means:
1. Get the vehicle moving with real sensors active and logging.
2. Watch how `/odometry/filtered` behaves — too jittery/noisy usually means the relevant diagonal value is too high (filter trusting raw sensor noise too much); too sluggish to track real motion usually means it's too low.
3. Adjust the specific diagonal entry for the field that's misbehaving, retest.

This is a more open-ended process than PID tuning (no simple P→D→I recipe) — budget real bench/pool time for it once more sensors are actively fused, rather than expecting a quick fix.

## Known limitations

- `pose0` (depth) and `odom0` (DVL velocity) are written but inactive — see table above.
- `process_noise_covariance` is untuned.
- This package has no tests/validation of its own beyond what each individual sensor's doc already covers — correctness here is really "did each sensor verify its own data before being wired in," not something to validate at the EKF level directly.
- 
