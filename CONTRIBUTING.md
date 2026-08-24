# Contributing to AUV Software

This file describes **how** we write and organize code in this repo — not what the code does. If you're looking for setup instructions, see [`README.md`](README.md) and [`docs/architecture-roadmap.md`](docs/architecture-roadmap.md) instead.

Read this once when you join, and skim it again occasionally — it's short on purpose. The point isn't to memorize it, it's to know these rules exist so the codebase stays readable for whoever joins after you.

---

## Why this file exists

This project gets worked on by many people over many years, most of whom never met each other. Without agreed-on conventions, every new contributor makes slightly different choices, and the codebase slowly turns into something nobody — including its own authors a year later — can confidently read. This file is the team's agreement on a shared set of habits, so the codebase stays consistent no matter who's currently active.

---

## Documentation — four layers, each with a job

Every piece of code in this repo should be documented at the right layer. Don't skip a layer just because another one exists.

1. **Root `README.md`** — the big picture: what this whole project is, how to set it up. Rarely changes.
2. **Each package's own `README.md`** — what that specific package does, what its nodes publish/subscribe to, and what its parameters are. Update this whenever you add or change a node in that package.
3. **Comments in config/launch/YAML files** — explain non-obvious values, especially units and where a number came from:
   ```yaml
   imu0_config: [false, false, false,   # x, y, z position — not measured by IMU
                 true,  true,  true,    # roll, pitch, yaw — trust this
                 ...
   ```
4. **Docstrings at the top of every node file** — what this node does, what it subscribes to, what it publishes, in a few lines:
   ```python
   """
   depth_pid_node.py

   Subscribes:  /odometry/filtered (nav_msgs/Odometry) — current depth
   Publishes:   /auv/wrench/depth (geometry_msgs/Wrench) — z-force output
   """
   ```

**Rule of thumb:** if you had to think for more than a few seconds to write a line of code, leave a comment explaining *why*, not just *what* — the code already shows what it does; comments should explain the reasoning a reader can't see just from reading the syntax.

---

## Adding a sensor

Every sensor gets a doc built from **`docs/sensors/_template.md`**, saved as `docs/sensors/<sensor-name>.md`. This isn't optional — a sensor without this doc is effectively undocumented no matter how good its code comments are, since this is where wiring, calibration, and PID tuning history live. See the template itself for what each section expects.

---

## Adding a new package

Before creating a new package, ask: *"Is this a new responsibility, a new dependency, or something independently reusable?"* If yes to any of those, it's a new package. If it's tightly related to an existing package's job, add to that package instead. (Full reasoning and examples on this are in `docs/architecture-roadmap.md`.)

Every new package needs, from the start:
- A `README.md` (see layer 2 above)
- A `package.xml` with an accurate one-line `<description>`

---

## Git workflow

- **Branch per feature/fix**, not committing directly to `main`. Name branches descriptively: `depth-pid-tuning`, `add-pressure-sensor-driver`, not `fix` or `updates`.
- **Commit messages** should say *what changed and why*, not just "update file." Good: `"Add pressure sensor driver, publishes to /pressure/depth"`. Not helpful: `"changes"`.
- **Pull requests, not direct pushes to `main`**, once more than one person is active — even a quick self-review before merging catches a surprising number of mistakes.
- **Update the relevant docs in the same PR as the code change.** If your code change makes a README or the sensor doc out of date, that PR isn't done until the doc is updated too — this is the single biggest thing that keeps documentation from going stale.

---

## Code style basics

- **One node per file**, matching the convention already used across this repo.
- **Descriptive names over short ones.** `depth_pid_node.py`, not `dpn.py`.
- **Don't hardcode tunable values** (PID gains, topic names, thresholds) in code — put them in a YAML config file the node reads at launch, so changing a value doesn't require editing and rebuilding code (see the Parameters section of the roadmap doc).

---

## If you're not sure

Ask in the club group chat, or ask whoever's currently active on the package you're touching. Guessing and getting it wrong is a completely normal part of a first PR — a reviewer catching a convention miss is what code review is for, not a sign you did something wrong by trying.
