# WIRED AUV Repository 2026-2027

Welcome! This repository holds all the code that runs on our AUV (Autonomous Underwater Vehicle) — the robot our club builds and programs for the annual RoboSub competition. It reads data from the vehicle's sensors, figures out where the vehicle is and which way it's pointing, and controls the thrusters to make it move on its own, without a person driving it.

**New to the team, or new to ROS2/Git in general? Start at [`docs/concepts/ros-basics.md`](docs/concepts/ros-basics.md)** — every term used in this README is explained there. This document assumes you're already comfortable with that vocabulary and just need to find your way around.

---

## Repo structure

Each folder here is a **package** with one specific job:

| Folder | What it's responsible for |
|---|---|
| `auv_bringup` | Launching everything together — the "start the robot" scripts |
| `auv_msgs` | Custom data formats shared between other packages |
| `auv_localization` | Figuring out where the vehicle is and which way it's facing, using sensor data |
| `auv_control` | Keeping the vehicle stable and controlling the thrusters |
| `auv_vision` | Using the camera to recognize objects (gates, buoys, etc.) |
| `auv_mission` | Deciding what the vehicle should be doing at each moment during a competition run |
| `auv_vn100` | Custom driver for the VectorNav VN-100 orientation sensor |

You'll also see a few folders like `ping_sonar_ros`, `zed-ros2-wrapper`, and `yolo_ros` appear on your computer once you're set up — these are **not written by us**. They're existing, free code written by other people/companies for our specific sensors and camera, which we pull in rather than write ourselves. You won't see these folders on GitHub itself — see `dependencies.repos` below for why.

### Key files at the repo root

| File | Purpose |
|---|---|
| `dependencies.repos` | List of external sensor/camera driver code to download, and which version. Read automatically by `setup.sh` — you never manually download these. |
| `setup.sh` | Sets up a freshly cloned copy of this repo on a new computer, including running `dependencies.repos`. |
| `.gitignore` | Tells Git which files/folders to never upload to GitHub (external driver code, build artifacts, etc). |
| `CONTRIBUTING.md` | Team conventions: git/branch workflow, documentation structure, when to create a new package. |

---

## Documentation map

| Location | What's there |
|---|---|
| [`docs/architecture-roadmap.md`](docs/architecture-roadmap.md) | The full technical build plan — system architecture, how the sensors and control loops fit together, and the order we're building things in. |
| [`docs/jetson-setup.md`](docs/jetson-setup.md) | Step-by-step Jetson + ROS2 Humble setup, from a bare board to a working environment. |
| `docs/sensors/` | One page per sensor — what it does, how it's wired, how to run and calibrate it, troubleshooting. Start here if you're working on a specific sensor. |
| `docs/concepts/` | Explains the *why* behind things we use — Kalman filters, PID control, quaternions, udev rules, basic ROS2/Git terminology. Read these when you want to understand a concept, not just run a command. |
| `docs/references/` | Quick-lookup command sheets — common ROS2 CLI commands, the standard node code pattern, build/launch usage, git/GitHub commands. Read these when you know what you want to do and just need the exact command. |
| `docs/issues/` | Deeper write-ups on open decisions that require multiple sub-team or sub-task participation. |

---

## Getting set up

Full step-by-step instructions with exact commands live in **[`docs/jetson-setup.md`](docs/jetson-setup.md)**. The short version:

1. Install ROS2 Humble on a computer running Ubuntu 22.04.
2. Clone this repo into a folder that will become your ROS2 workspace's `src` folder.
3. Run `setup.sh` to pull in external sensor/camera driver code.
4. Build the workspace with `colcon build`.
5. Continue to [`docs/architecture-roadmap.md`](docs/architecture-roadmap.md) for running individual sensors and eventually the full system.

If you get stuck at any step, that's completely normal — ask in the club's group chat, or bring your laptop to a meeting.

---

## A note for new members

Everyone on this team started exactly where you are now — this codebase looks like a lot at first, and that's expected, not a sign you're behind. Read [`docs/concepts/ros-basics.md`](docs/concepts/ros-basics.md) first, then a package's own `README.md` before diving into its code, ask questions early rather than getting stuck alone, and don't worry about "breaking" anything — Git means your changes are never permanently destructive, and mistakes are a normal part of learning this.
