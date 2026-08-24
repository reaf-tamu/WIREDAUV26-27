# AUV Software

Welcome! This repository holds all the code that runs on our AUV (Autonomous Underwater Vehicle) — the robot submarine our club builds and programs for the RoboSub competition. It reads data from the vehicle's sensors, figures out where the vehicle is and which way it's pointing, and controls the thrusters to make it move on its own, without a person driving it.

This README assumes you've never done anything like this before. If a term seems unfamiliar, check the glossary below before anything else — every unfamiliar word you'll hit in this repo should be explained somewhere in this doc.

---

## First, some terms

You'll see these words constantly in this repo and in conversations with the team. Come back to this section any time something doesn't make sense.

- **Repository (or "repo")** — a folder of code and files that's tracked by a tool called Git (below), usually hosted online on GitHub. This whole project — everything you're looking at right now — is one repo.
- **Git** — a program that tracks every change ever made to the files in a repo, so nothing is ever truly lost, and multiple people can work on the same code without overwriting each other. It runs entirely on your own computer.
- **GitHub** — a website that hosts Git repos online, so the team can share code, see each other's changes, and work together. Git is the tool; GitHub is where our copy of the repo lives online.
- **Terminal** (also called "command line" or "shell") — a text-based way to control your computer, by typing commands instead of clicking icons. Almost everything in this repo is done through the terminal. This is normal and everyone feels slow at first — it gets faster with repetition.
- **Command** — a single instruction you type into the terminal and press Enter to run. Example: `git status` is a command that shows what's changed in your repo.
- **ROS2 (Robot Operating System 2)** — the software framework our robot's code is built on. Despite the name, it's not an actual operating system (like Windows or macOS) — it's a set of tools that let separate pieces of code (see "Node" below) talk to each other easily. It's the standard tool used across most robotics teams and companies, which is also why it's worth learning well.
- **Node** — one individual running program with one specific job. For example, one node reads data from a sensor; a different node decides how fast the thrusters should spin. Keeping jobs separate like this means if one node crashes, the rest of the robot keeps working.
- **Package** — a folder containing one or more related nodes, plus the files ROS2 needs to build and run them. This repo is made up of several packages, each responsible for a different part of the robot (see "What's in this repo" below).
- **Workspace** — the overall folder on your computer where ROS2 packages live and get built together. This repo becomes the `src` (source) folder inside your workspace — more on this in Getting Set Up.
- **Build** — the process of turning the code you've written into something the computer can actually run. In ROS2, this is done with a tool called `colcon`.
- **Sudo** — short for "superuser do." Typing `sudo` before a command runs it with full administrator permissions, similar to right-clicking "Run as Administrator" on Windows. You'll need it for things like installing software, but it's powerful — never run a `sudo` command you don't understand.

---

## What's in this repo

Each folder here is a **package** (see glossary) with one specific job:

| Folder | What it's responsible for |
|---|---|
| `auv_bringup` | Launching everything together — the "start the robot" scripts |
| `auv_msgs` | Custom data formats shared between other packages |
| `auv_localization` | Figuring out where the vehicle is and which way it's facing, using sensor data |
| `auv_control` | Keeping the vehicle stable and controlling the thrusters |
| `auv_vision` | Using the camera to recognize objects (gates, buoys, etc.) |
| `auv_mission` | Deciding what the vehicle should be doing at each moment during a competition run |

You'll also see a few folders like `vectornav`, `zed-ros2-wrapper`, and `yolo_ros` appear on your computer once you're set up — these are **not written by us**. They're existing, free code written by other people/companies for our specific sensors and camera, which we pull in rather than write ourselves. You won't see these folders on GitHub itself — see `dependencies.repos` below for why.

A couple of other important files at this top level:
- **`dependencies.repos`** — a list telling your computer which external code (like the driver folders above) to download, and exactly which version of it. A tool automatically reads this file and does the downloading for you — you never need to manually find or download these yourself.
- **`setup.sh`** — a script (a saved sequence of commands) that sets up a freshly cloned copy of this repo on a new computer, including downloading everything listed in `dependencies.repos`.
- **`.gitignore`** — tells Git which files/folders to ignore and never upload to GitHub (like the external driver code above, and files your computer generates automatically when building).

---

## Getting set up

This is a multi-step process the first time, but you only do it once per computer/Jetson. Full step-by-step instructions with exact commands live in **[`docs/architecture-roadmap.md`](docs/architecture-roadmap.md)** — this section is just the big picture so the steps make sense when you get there.

1. **Install ROS2 Humble** on a computer running Ubuntu 22.04 (a specific version of Linux). This is the framework everything else depends on.
2. **Clone this repo** into a folder that will become your ROS2 workspace's `src` folder.
3. **Run `setup.sh`**, which downloads the external sensor/camera driver code listed in `dependencies.repos`.
4. **Build the workspace** using `colcon build` — this compiles everything into a runnable form.
5. You're set up! From here, `docs/architecture-roadmap.md` walks through running individual sensors and eventually the full system.

If you get stuck at any step, that's completely normal — ask in the club's group chat, or bring your laptop to a meeting. Setup issues are usually quick to fix once someone can see your screen.

---

## Where to find more

- **[`docs/architecture-roadmap.md`](docs/architecture-roadmap.md)** — the full technical build plan: exact setup commands, how the sensors and control loops fit together, and the order we built things in.
- **`docs/sensors/`** — one page per sensor, covering what it does, how it's wired, and how to run its code. Start here if you're working on a specific sensor.
- **[ROS2 official documentation](https://docs.ros.org/en/humble/)** — the official docs for the exact ROS2 version we use (Humble).

---

## A note for new members

Everyone on this team started exactly where you are now — this codebase looks like a lot at first, and that's expected, not a sign you're behind. Read through a package's own `README.md` before diving into its code, ask questions early rather than getting stuck alone, and don't worry about "breaking" anything — Git means your changes are never permanently destructive, and mistakes are a normal part of learning this.
