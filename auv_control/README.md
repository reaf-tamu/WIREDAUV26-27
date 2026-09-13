# auv_control

PID control loops and thruster allocation — takes the vehicle's current state (from `auv_localization`) and a desired state (from mission logic or manual testing), and turns the difference into actual thruster commands.

## What's in this package

| File | Role |
|---|---|
| `auv_control/pid.py` | Generic, reusable PID controller class. See `docs/concepts/pid-control.md` for what each term does. |
| `auv_control/attitude_control_node.py` | Runs all 6 PID loops (roll, pitch, yaw, depth, altitude, surge). Reads `/odometry/filtered` + `/ping1d/range` + `/auv/setpoint`, publishes `/auv/wrench`. |
| `auv_control/thruster_allocator_node.py` | Converts a `Wrench` into 8 individual thruster angle commands, based on confirmed thruster positions. Reads `/auv/wrench`, publishes `/auv/thruster_commands`. |
| `auv_control/thruster_interface_node.py` | The only node that actually talks to hardware — drives the PCA9685 servo/ESC board. Reads `/auv/thruster_commands`. |
| `config/pid_gains.yaml` | All tunable PID gains. Edit this to tune, not the Python code. |
| `launch/attitude_control.launch.py` | Launches `attitude_control_node` with `pid_gains.yaml` loaded. |

## Thruster layout

Confirmed physical positions (sitting in the vehicle facing forward):

**Horizontal (surge/yaw):**
```
A1 = back-left    A4 = front-left
M1 = back-right   M4 = front-right
```

**Vertical (heave/roll/pitch):**
```
A3 = front-left   A2 = back-left
M3 = front-right  M2 = back-right
```

A-side and M-side thrusters are mounted with mirrored prop orientation — this is why `SURGE_SIGN` in the allocator gives A and M thrusters opposite signs for the same commanded surge, even though they're both just "moving forward."

## Degrees of freedom: what actually works right now

| DOF | Sensor feedback | Actuation | Status |
|---|---|---|---|
| Yaw | Real (VN-100 → EKF) | Real, structure known | Bench sign check required before use — see `YAW_MIXING_VERIFIED` |
| Altitude | Real (Ping Sonar, direct — not via EKF) | Real (heave group) | Bench sign check recommended for the new code path — see `docs/sensors/vn100.md`/`ping-sonar.md` tuning logs |
| Roll | Real (VN-100 → EKF) | Real, structure known | Bench sign check required — see `ROLL_MIXING_VERIFIED` |
| Pitch | Real (VN-100 → EKF) | Real, structure known | Bench sign check required — see `PITCH_MIXING_VERIFIED` |
| Depth | **Not yet** — no pressure sensor wired into the EKF | Real (heave group, shared with altitude) | Not usable until pressure sensor exists |
| Surge | **Not yet** — no DVL fused into the EKF | Real | Only open-loop possible until DVL exists |
| Sway | N/A | **Not physically possible** with this thruster layout | Not implemented |

**Every one of the "structure known, bench sign check required" loops is gated by a `_MIXING_VERIFIED` flag in `thruster_allocator_node.py`, defaulting to `False`.** This means the PID computes a real, correct-shaped output, but the allocator silently zeroes it out until someone has physically confirmed the direction is right and flipped the flag. This is deliberate — see that file's docstring for the exact bench-test procedure. **Never flip a `_MIXING_VERIFIED` flag without having actually done the corresponding physical test.**

## Running it

Full stack (with sensors):
```bash
ros2 launch auv_bringup bringup.launch.py
```
Then, in separate terminals (not yet folded into `bringup.launch.py`):
```bash
ros2 launch auv_control attitude_control.launch.py
ros2 run auv_control thruster_allocator_node
ros2 run auv_control thruster_interface_node
```

`thruster_interface_node` will attempt to arm the ESCs on startup — listen for two beeps, same as the original hardcoded script.

## Tuning

Edit `config/pid_gains.yaml`, then restart `attitude_control_node` — no rebuild needed for a YAML-only change. Full step-by-step tuning procedure, safety checklist, and unit gotchas (radians for angles, meters for altitude) are written up separately — ask whoever ran the last tuning session, or check the relevant sensor doc's tuning log (`docs/sensors/vn100.md`, `docs/sensors/ping-sonar.md`) for prior results before starting from scratch.

## Manual testing without a mission running

Publish a wrench directly to test the allocator/thrusters in isolation:
```bash
ros2 topic pub /auv/wrench geometry_msgs/msg/Wrench "{force: {x: 0.5}}" --once
```

Publishing a real `Setpoint` by hand requires a quaternion, which is painful to type manually — small helper scripts exist for this (ask around, or check recent tuning session notes) rather than hand-constructing one from `ros2 topic pub`.

## Safety notes

- Secure the vehicle in a bench/stand before ever running real thruster commands — every DOF above except depth/surge is either untested or only partially verified.
- Keep hands clear of all 8 thrusters once `thruster_interface_node` is running and armed.
- `thruster_interface_node` returns every thruster to neutral on shutdown (including Ctrl+C or a crash) — but don't rely on this as your only safety measure; a hard power cut is always the fastest real stop.
- The allocator clamps every output to 60°-120° (`clamp_angle`) — a conservative range matching prior tested-safe values, not derived from a thruster spec sheet. Widen deliberately, not by accident.

## Known limitations

- Roll/pitch/yaw sign conventions are structurally correct but not all bench-verified yet — check each `_MIXING_VERIFIED` flag's current state before assuming a loop is live.
- Depth and surge have no real sensor feedback yet (pressure sensor and DVL respectively, neither wired into the EKF as of this writing).
- Sway is not achievable with the current thruster layout — see `docs/issues/` for the team's mounting/vectored-thruster discussion if this becomes a priority.
- `auv_msgs/Setpoint`'s `use_altitude_hold` flag repurposes `desired_pose.position.z` to mean "desired altitude" rather than "desired depth" when set — a slightly unusual overload worth remembering rather than assuming based on the field name alone.
