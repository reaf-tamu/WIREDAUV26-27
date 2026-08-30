# Euler angles & quaternions

## The problem: how do you represent "which way something is facing"?

Any rigid object in 3D space has an orientation — which way it's pointing. There are several different mathematical ways to write that orientation down as numbers, and our stack actually uses two of them side by side: **Euler angles** (roll, pitch, yaw) because they're intuitive for humans, and **quaternions** because they're what ROS, our EKF, and our own driver code actually pass around internally. Understanding both, and why we bother converting between them, makes a lot of otherwise-confusing code (like `vn100_ascii_node.py`'s `euler_deg_to_quaternion()`) make sense.

## Euler angles: the intuitive one

**Roll, pitch, and yaw** describe an orientation as three separate rotations, one around each axis:
- **Roll** — rotation about the forward axis (banking left/right)
- **Pitch** — rotation about the side-to-side axis (nose up/down)
- **Yaw** — rotation about the vertical axis (turning left/right, i.e. heading)

This is how humans naturally think and talk about orientation ("we're pitched down 10 degrees"), and it's exactly what the VN-100 reports in its `$VNYMR` sentence, and what your team will mostly discuss out loud on the pool deck.

### The real flaw: gimbal lock

Euler angles have a genuine mathematical problem, not just an inconvenience: **gimbal lock**. As pitch approaches ±90°, the yaw and roll axes rotate to become aligned with each other — you effectively lose one whole independent axis of rotation. Right at and near that point, tiny real changes in orientation can require large, sudden jumps in the reported yaw/roll numbers to represent — and averaging or smoothly interpolating between two Euler-angle orientations near that region can produce physically nonsensical in-between values.

This isn't a rare edge case you can just avoid by "not pitching that far" — it's a structural property of representing 3D rotation with three independent numbers taken one axis at a time. Any system that does serious internal math on orientation (like our EKF, constantly blending predictions and corrections) needs a representation that doesn't have this failure mode.

## Quaternions: the one without the flaw

A **quaternion** represents the same rotation using **four** numbers instead of three: `(x, y, z, w)`. Conceptually, the `x, y, z` part encodes an axis to rotate around, and `w` encodes how far to rotate around it (specifically, related to the cosine of half the rotation angle — more on that "half" below). Because it's not built by composing three separate single-axis rotations in sequence, it has no equivalent singularity — every orientation maps to a well-behaved point, and interpolating between two of them produces sensible in-between orientations.

**This is why `sensor_msgs/Imu` and every other ROS orientation message use a quaternion field, never separate roll/pitch/yaw fields.** It's also why `robot_localization`'s EKF does all of its internal math on quaternions, not Euler angles — the constant blending of predicted and measured orientation is exactly the kind of operation that breaks down near gimbal lock if done on Euler angles directly.

**The tradeoff:** quaternions are not intuitive to read at a glance. Nobody looks at `(x: 0.008, y: -0.016, z: -0.486, w: 0.874)` and immediately knows the vehicle's roughly facing. That's precisely why we still convert back to Euler angles anytime a human needs to read or reason about orientation directly (debug scripts, this doc's examples, verbally describing vehicle attitude) — Euler angles for people, quaternions for the math.

## Converting between them

### Euler → quaternion

This is what `euler_deg_to_quaternion()` in `auv_vn100/auv_vn100/vn100_ascii_node.py` does — the VN-100 gives us human-readable yaw/pitch/roll in its `$VNYMR` sentence, but we need to publish a proper ROS `sensor_msgs/Imu` message, which requires a quaternion.

**Step 1 — each single-axis rotation is itself a small quaternion.** A quaternion representing "rotate by angle θ around one specific axis" has a simple, direct formula: put `cos(θ/2)` in `w`, and put `sin(θ/2)` in whichever of x/y/z matches that axis, with the other two left at zero. So:

- "Rotate by yaw around Z" → the quaternion `(x=0, y=0, z=sin(yaw/2), w=cos(yaw/2))`
- "Rotate by pitch around Y" → `(x=0, y=sin(pitch/2), z=0, w=cos(pitch/2))`
- "Rotate by roll around X" → `(x=sin(roll/2), y=0, z=0, w=cos(roll/2))`

This is exactly where the six variables in the code come from — they aren't arbitrary trig calls, they're literally the `w` and one nonzero component of each of these three simple, single-axis quaternions:
```python
cy = math.cos(yaw * 0.5)    # w-component of the "yaw" quaternion
sy = math.sin(yaw * 0.5)    # z-component of the "yaw" quaternion
cp = math.cos(pitch * 0.5)  # w-component of the "pitch" quaternion
sp = math.sin(pitch * 0.5)  # y-component of the "pitch" quaternion
cr = math.cos(roll * 0.5)   # w-component of the "roll" quaternion
sr = math.sin(roll * 0.5)   # x-component of the "roll" quaternion
```

**Step 2 — combine the three rotations by multiplying their quaternions together.** Quaternions have their own multiplication rule (similar in spirit to how you'd multiply complex numbers, but extended to four components, and — importantly — order matters: multiplying `A * B` doesn't generally give the same result as `B * A`, which is exactly why the ZYX *order* was specified up front). Multiplying two quaternions together produces a third quaternion representing "do this rotation, then that one" — so multiplying our three single-axis quaternions together, in ZYX order, produces one combined quaternion representing the whole yaw-then-pitch-then-roll rotation as a single object.

**Step 3 — the code skips straight to the answer.** If you actually carried out that multiplication by hand (multiply the yaw quaternion by the pitch quaternion, then multiply that result by the roll quaternion, using the quaternion multiplication rule each time), and simplified the algebra, you'd end up with exactly these four expressions:
```python
w = cr * cp * cy + sr * sp * sy
x = sr * cp * cy - cr * sp * sy
y = cr * sp * cy + sr * cp * sy
z = cr * cp * sy - sr * sp * cy
```
Nobody derives this from scratch in working code — it's a well-known standard result, and the function just implements the already-simplified formula directly, skipping the three intermediate multiplication steps. But knowing that each line traces back to "three simple rotations, multiplied together, then algebraically flattened" is what turns this from a black-box formula into something you could actually reconstruct if you had to.

**Why half the angle, not the full angle?** This is a real property of quaternion algebra, not an arbitrary implementation detail, and it's baked into Step 1 above: a quaternion representing a rotation by angle θ is defined using `cos(θ/2)` and `sin(θ/2)`, never `cos(θ)`/`sin(θ)` directly. This falls out of how quaternion multiplication composes rotations — combining a "rotate by θ/2" quaternion with itself, via the multiplication rule from Step 2, produces a quaternion representing a rotation by the full θ, not by θ/2 + θ/2 = θ in some simpler additive sense. The halving is what makes the composition rule work out correctly; it's deliberate and correct, not a bug, the first time you see it in code.

### Quaternion → Euler

The reverse direction — going from a quaternion back to a human-readable yaw/pitch/roll — comes up anytime you want to *read* an orientation rather than just pass it along. We use this pattern in debug tooling (e.g. printing live roll/pitch/yaw while verifying the VN-100's orientation) and inside `attitude_control_node.py`'s `quaternion_to_yaw()` helper, which extracts just the yaw component needed for the yaw PID loop:

```python
def quaternion_to_yaw(q):
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)
```

Note this only pulls out yaw, not all three angles — because that's the only one the current control code actually needs. The full inverse conversion (all of roll, pitch, and yaw from a quaternion) follows the same kind of closed-form formula as the forward direction, just algebraically rearranged.

**A subtlety worth knowing, since it's already bitten us once:** `atan2` naturally wraps around at ±180° — a heading of 179° and a heading of -179° are only 2° apart in reality, but a naive subtraction of the two raw numbers would compute a ~358° difference. This is exactly why `attitude_control_node.py` has a `shortest_angle_diff()` helper before feeding yaw error into the PID loop — the PID math itself has no concept of angle wraparound, so it has to be handled explicitly, every time you compute a difference between two angles.

## How ROS sets this up

- **Message field order is `(x, y, z, w)`**, not `(w, x, y, z)` — this trips people up since some other libraries/fields (math textbooks especially) list `w` first. Every quaternion field in ROS (`geometry_msgs/Quaternion`, and the `orientation` field inside `sensor_msgs/Imu`) follows the `x, y, z, w` order. Our driver's `euler_deg_to_quaternion()` returns values in that same order specifically to match.
- **ROS's standard axis convention is ENU (East-North-Up), right-handed** — x forward, y left, z up (this is REP-103, ROS's formal convention document). This matters because a sensor's *native* convention won't necessarily match — the VN-100 natively reports in NED (North-East-Down), which is why frame conventions and mounting transforms matter so much (see `docs/sensors/vn100.md` section 8) — getting the axis convention wrong produces a quaternion that's numerically valid but describes the wrong physical rotation.
- **`tf2`** (ROS's transform library) works entirely in quaternions internally for exactly the reasons above, and is what actually applies our VN-100 mounting-offset static transform to rotate the sensor's raw orientation into the vehicle's `base_link` frame before the EKF ever sees it.

## How we use this in the club

- **`vn100_driver`**: converts the VN-100's native Euler-angle output into a quaternion, to publish a spec-compliant `sensor_msgs/Imu` message.
- **The static mounting transform** (`vectornav_mount_tf`, in `auv_bringup`'s launch file): itself stored and applied as a rotation via `tf2`, using the same quaternion machinery under the hood — even though we specified it in easier-to-reason-about roll/pitch/yaw degrees when creating it.
- **`robot_localization`'s EKF**: fuses orientation entirely in quaternion form internally, for the gimbal-lock reasons above, and outputs `/odometry/filtered` with its orientation as a quaternion too.
- **`attitude_control_node.py`**: converts the EKF's quaternion output back into a single yaw angle (Euler, but just the one axis) — because that's what a human-intuitive PID setpoint and error actually need to be computed against.

The pattern across our whole stack is consistent: **quaternions live at every boundary between systems (sensor → ROS message → EKF → downstream code), and Euler angles get reintroduced only at the last moment, right where a human or a simple single-axis control loop actually needs a plain number.**

## Resources to learn more

- **[Visualizing quaternions (4d numbers) with stereographic projection — 3Blue1Brown](https://www.3blue1brown.com/lessons/quaternions)** — genuinely the best available intuition-building resource on what a quaternion actually is and why the math works, if you want to go beyond "here's the formula, trust it."
- **[REP 103 — Standard Units of Measure and Coordinate Conventions](https://www.ros.org/reps/rep-0103.html)** — the actual ROS specification for axis conventions (ENU, right-handed) and quaternion field ordering referenced above.
