# The Kalman Filter

## The problem it solves

Every sensor lies to you a little. Your VN-100 says you're at 12.3° pitch, but if you asked it again a millisecond later it might say 12.1° or 12.5° — not because the vehicle actually moved, but because real sensors have noise. At the same time, you usually have *some* independent idea of what the vehicle should be doing (it was rotating at some rate a moment ago, so it's probably still close to that rate now).

A Kalman filter's whole job is to combine "what I predicted would happen" with "what my noisy sensor just told me" into a single estimate that's better than either one alone.

## The intuition: a weighted average that knows what to trust

Imagine you're guessing your friend's weight. You guess 150 lbs, but you're not totally sure — maybe ±10 lbs. Then a scale says 160 lbs, but that scale is old and sketchy — maybe ±20 lbs of error. What's your best guess now?

You shouldn't just average them (155 lbs), and you shouldn't just trust the scale outright either. You should lean *more* toward whichever number you're more confident in. Since your guess (±10) is more trustworthy than the sketchy scale (±20), your new best estimate should land closer to 150 than to 160 — maybe around 154.

That's the entire idea behind a Kalman filter, formalized: **it's a weighted average, where the weights come from how confident you are in each source.** The filter tracks that confidence (called *covariance*) for both its own predictions and every sensor's measurements, and constantly recalculates how much to trust each one.

## The predict/update cycle

A Kalman filter runs in a loop, two steps per cycle:

1. **Predict** — using a model of how the system behaves (e.g. "if the last known angular velocity was X, the vehicle has probably rotated by roughly X × time_elapsed since then"), project the state forward to right now. This step *always* makes the filter's confidence a little worse — predictions drift the longer you go without a real measurement to correct them.

2. **Update (a.k.a. correct)** — when a new sensor reading arrives, compare it to the prediction. Blend them using the weighted-average idea above. This step makes the filter's confidence better, because now it has fresh outside information.

Repeat forever, many times a second. The result is a smooth, continuously-updated best estimate of the vehicle's state — one that's more stable than raw sensor readings and more accurate than dead-reckoning prediction alone.

## Why "Extended" Kalman Filter (EKF)?

The plain Kalman filter assumes everything is linear (rotations, in particular, are not — a small change in yaw doesn't affect x/y position in a simple straight-line way). The **Extended** Kalman Filter (EKF) handles this by locally approximating the nonlinear motion with something linear-ish at each step, close enough to work well in practice. This is the version almost every mobile robot and AUV actually uses, ours included.

## Sensor fusion: the real reason we care

A Kalman filter isn't limited to one sensor correcting one prediction — you can feed it measurements from *several* sensors, each contributing whatever piece of the state it's actually good at measuring:

- An IMU is great at orientation and angular velocity, but accumulates drift in position over time if you try to integrate it into a position estimate.
- A DVL is great at velocity, but says nothing about orientation.
- A depth/pressure sensor is great at exactly one number (depth) and nothing else.

None of these alone gives you a full, reliable picture of "where is the vehicle and how is it moving." A Kalman filter fuses all of them together, each sensor correcting the parts of the state it's actually qualified to speak to, and letting the prediction step fill in the gaps between measurements. This is why it sits at the center of the state estimation stage in our architecture — it's the thing that turns a pile of individually-imperfect sensors into one trustworthy estimate.

## How this works in ROS2

We don't write our own Kalman filter math — this is a well-solved problem, and the standard ROS2 package for it is **[`robot_localization`](https://github.com/cra-ros-pkg/robot_localization)**, developed by Charles River Analytics. It provides a ready-made `ekf_node` that does exactly the predict/update cycle described above, and all you configure is:

- **Which topics to fuse**, and which specific fields to trust from each one. A topic might publish a dozen values, but you can tell the EKF to only use *some* of them — for example, trusting an IMU's orientation and angular velocity but ignoring its raw acceleration.
- **How much to trust your own motion model** (`process_noise_covariance`) — this is a knob you tune, representing how much you expect the vehicle's true state to wander between updates.
- **How fast to run the whole loop** (`frequency`).

The node outputs one clean, fused estimate on a single topic (conventionally `/odometry/filtered`) — a `nav_msgs/Odometry` message carrying position, orientation, and velocity, with proper covariance attached. Everything downstream (our PID controllers, in our case) reads from that one topic instead of juggling raw sensor topics itself.

## How we use it in the club

Our `auv_localization` package launches `robot_localization`'s `ekf_node`, configured in `config/ekf.yaml`. Right now it fuses:

- **VN-100 orientation and angular velocity** (`/vectornav/imu`) — roll, pitch, yaw, and their rates.

Wired in but commented out until the hardware is on the vehicle:
- **Depth from the pressure sensor**, once a small converter node publishes it as a pose the EKF can consume.
- **Velocity from the DVL**, once it's connected — this will give the filter real surge/sway velocity instead of having to infer it, which matters a lot for controlling forward motion accurately.

The filter's output feeds directly into our 6 PID control loops (roll/pitch/yaw/depth/surge/sway) — none of those loops ever talk to a raw sensor topic directly. They all read the single fused estimate from `/odometry/filtered`, which is the entire point of running the EKF in the first place: one clean number to control against, instead of six sensors' worth of noisy, disagreeing raw data.

## Resources to learn more

- **[How a Kalman Filter Works, in Pictures](https://www.bzarg.com/p/how-a-kalman-filter-works-in-pictures/)** — the best beginner-friendly, visual walkthrough of the actual math. Start here if you want to understand *why* the equations look the way they do, not just that they work.
- **[Kalman Filter — Wikipedia](https://en.wikipedia.org/wiki/Kalman_filter)** — solid reference for terminology and the formal definition once the intuition above makes sense.
- **[`robot_localization` GitHub repo](https://github.com/cra-ros-pkg/robot_localization)** — the actual package we use. Its README and wiki cover every config parameter in detail; worth reading before tuning `ekf.yaml` for real.
