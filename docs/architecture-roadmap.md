# Architecture Roadmap

This document explains two things: **how the whole robot's software fits together**, and **the order we build it in**. If `README.md` was "what is this project," this is "how does it actually work, and what do I build first."

This assumes you've already read the glossary in the root `README.md`. Anything new gets explained here as it comes up.

---

## Part 1: The big picture

Before touching any code, it helps to understand what the vehicle's software is actually trying to do, moment to moment. Here's the whole loop in plain language:

**Step 1 — Sensors measure things about the vehicle.**
Different sensors are good at measuring different things:
- The **VN-100** (an IMU, or "inertial measurement unit") measures which way the vehicle is tilted and how fast it's rotating.
- The **pressure sensor** measures how deep underwater the vehicle is.
- The **DVL** (Doppler Velocity Log) measures how fast the vehicle is moving.
- The **Zed mini camera** captures images of what's around the vehicle.

None of these sensors know the full picture on their own — each one only measures its own small piece.

**Step 2 — A "state estimator" combines all of that into one answer.**
A **state estimator** is a piece of code whose whole job is: take numbers from every sensor and combine them into one best guess of "where is the vehicle, which way is it facing, and how fast is it moving right now." We use a well-known combining method called an **EKF** (Extended Kalman Filter) — you don't need to know how the math works, just that its job is to blend noisy, imperfect sensor readings into one trustworthy answer. This answer gets published (see `README.md`'s Node/Topic concepts) so any other part of the code can use it.

**Step 3 — A controller decides what the thrusters should do.**
Once we know where the vehicle actually is, we compare that to where we *want* it to be, and calculate how to close that gap. This is done with something called a **PID controller** — a small, well-known piece of math that looks at "how far off am I right now" and produces a smooth correction, rather than a jerky overreaction. We run a separate PID controller for each thing we're trying to hold steady: depth, heading, roll, and so on.

**Step 4 — Those corrections get converted into individual thruster commands.**
The PID controllers output a combined "push this way, twist that way" instruction (called a **wrench** — force + torque). A final step, called **thruster allocation**, converts that single combined instruction into individual speed commands for each physical thruster, based on where each thruster is mounted and which direction it points.

**A separate path — vision:**
The camera feed is handled differently, since it's not about "how is the vehicle currently positioned" but "what does the vehicle need to *do* right now." A vision model (**YOLO**) looks at the camera image and identifies objects — gates, buoys, markers — that matter for the competition. That information goes to the **mission planner**, which decides what the vehicle's current goal should be ("center on the gate," "move forward"), and sends that goal to the controllers from Step 3 as a new target.

**Put together, the loop runs continuously, many times per second:**
sensors → state estimator → (compared against a goal from the mission planner) → PID controllers → thruster allocation → thrusters move → sensors measure the new result → repeat.

---

## Part 2: Which package does which job

Each of the four steps above lives in its own package (see `README.md` for what a package is):

| Step | Package |
|---|---|
| Combining sensor data (state estimator) | `auv_localization` |
| Deciding thruster commands (PID + thruster allocation) | `auv_control` |
| Recognizing objects from the camera | `auv_vision` |
| Deciding the vehicle's current goal | `auv_mission` |
| Shared data formats used across packages | `auv_msgs` |
| Starting everything together | `auv_bringup` |

Each package has its own `README.md` with more specific detail — this document only covers the big picture of how they connect.

---

## Part 3: Build order

We don't build all of this at once — each stage below should give you something you can actually test before moving to the next. This is the order the team follows, and the reasoning for why.

### Stage 0 — Get your computer/Jetson ready
Install ROS2 Humble, and set up this repo as your ROS2 **workspace**'s `src` folder (the folder ROS2 looks in for packages). If you're setting up a fresh Jetson, ask a team lead — there are some Jetson-specific steps (like a required firmware update) that aren't part of a normal computer's setup, and it's much faster with someone who's done it before.

### Stage 1 — Get one sensor talking, and check it
Before writing any decision-making code, just confirm each sensor's data is actually flowing. Start with the VN-100:
```bash
ros2 launch vectornav vectornav.launch.py
ros2 topic echo /vectornav/imu
```
If you see numbers changing as you tilt the sensor by hand, it's working. Repeat this same idea for each sensor, one at a time — don't move on until each is confirmed individually. Debugging is much easier with one sensor at a time than with everything running at once and something quietly wrong.

### Stage 2 — Combine sensors into a state estimate
Once sensors are confirmed working, bring up the state estimator (`auv_localization`), and check that `/odometry/filtered` (its output topic) shows sensible numbers.

### Stage 3 — Build the control loop, and test on a bench first
Write the PID controllers and thruster allocation (`auv_control`). **Test this out of the water first** — power the vehicle in a stand, nudge it by hand, and confirm the thrusters push back in the correct direction. A backwards sign here is the most common first bug, and it's much safer to catch on a bench than underwater.

### Stage 4 — Bring up vision
Get the camera publishing images, then get the YOLO detection model running on that feed, and confirm it correctly identifies objects in a test image or video before trusting it live.

### Stage 5 — Connect vision to mission logic
Write the mission planner (`auv_mission`) so it turns "I see a gate" into an actual goal sent to the controllers — this is where the vehicle starts making its own decisions instead of just holding still.

### Stage 6 — Full integration and pool testing
With every piece individually working, test the whole loop together, first in a controlled setting, then in the pool. Expect this stage to surface bugs the earlier stages didn't — that's normal, and exactly why the earlier stages were tested individually first.

---

## Where to go from here

- **Working on a specific sensor?** Check `docs/sensors/` for that sensor's page — wiring, how to run its code, and its calibration/tuning history.
- **Adding new code?** Check `CONTRIBUTING.md` for how we document and organize things, so your work fits the same conventions as everyone else's.
- **Confused about a ROS2 term not covered here?** The [official ROS2 Humble documentation](https://docs.ros.org/en/humble/) is a good next stop, or ask in the club chat — there's no such thing as a bad question here, everyone starts confused by this stuff.
