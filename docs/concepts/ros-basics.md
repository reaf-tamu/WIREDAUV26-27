# ROS2 & repo basics

If you're new to this team, start here. These are the terms you'll hit constantly — in this repo, in code comments, in conversations with the team. Don't try to memorize this in one sitting; skim it once now, then come back to a specific section whenever something doesn't make sense.

---

## Part 1: Working with code

### Repository ("repo")

A folder of code and files, tracked by a tool called **Git**, so every change is recorded and nothing is ever truly lost.

> This whole project — everything you're looking at right now — is one repo.

### Git

The program that actually does the tracking. It watches every change to every file, so multiple people can work on the same code at the same time without overwriting each other.

> Runs entirely on your own computer. See [`docs/references/git-github.md`](../references/git-github.md) for the actual commands you'll use day to day.

### GitHub

A website that hosts Git repos online, so the whole team can share code and see each other's changes.

> **Git is the tool. GitHub is where our copy of the repo lives online.** These get confused constantly — they're not the same thing.

### Terminal

A text-based way to control your computer — typing commands instead of clicking icons.

> Almost everything in this repo happens through the terminal.

### Command

One instruction you type into the terminal and run by pressing Enter.

> Example: `git status` is a command. It shows what's changed in your repo.

### Sudo

Short for "superuser do." Puts a command into administrator mode — similar to right-clicking "Run as Administrator" on Windows.

> Needed for things like installing software. It's powerful — **never run a `sudo` command you don't understand.**

---

## Part 2: ROS2

### ROS2 (Robot Operating System 2)

The software framework our robot's code is built on.

> Despite the name, it's **not an operating system** like Windows or macOS. It's a set of tools that let separate pieces of code talk to each other easily. It's also the standard framework used across most robotics teams and companies — learning it well is a real, transferable skill.

### Node

One running program with one specific job.

> Example: one node reads data from a sensor. A completely different node decides how fast the thrusters should spin. Keeping jobs separate like this means if one node crashes, the rest of the robot keeps working.

### Topic

A named channel that nodes use to send data to each other.

> One node **publishes** data onto a topic (like `/vectornav/imu`). Any number of other nodes can **subscribe** to that same topic to receive it — the publisher never needs to know who, if anyone, is listening.

### Message

The actual data sent over a topic, in a fixed, predefined shape.

> A `sensor_msgs/Imu` message always has the same fields — orientation, angular velocity, and so on — no matter which topic it's traveling on. **The message type (its shape) and the topic name are two separate things:** the same type of message can flow over many differently-named topics.

### Package

A folder holding one or more related nodes, plus everything ROS2 needs to build and run them.

> This repo is made up of several packages, each responsible for one part of the robot — see the root `README.md` for the full list.

### Workspace

The overall folder on your computer where ROS2 packages live and get built together.

> This repo becomes the `src` (source) folder *inside* your workspace — they're not the same folder.

### Build

Turning the code you've written into something the computer can actually run.

> Done with a tool called `colcon`. See [`docs/references/build-and-launch.md`](../references/build-and-launch.md).

### Launch file

A file that starts a whole group of nodes together with one command.

> Instead of starting five nodes by hand in five terminals, one launch file starts all five at once, already wired up correctly. See [`docs/references/build-and-launch.md`](../references/build-and-launch.md).

---

## Where to go next

| If you want to... | Go to... |
|---|---|
| Learn actual Git/GitHub commands | [`docs/references/git-github.md`](../references/git-github.md) |
| Look up a specific ROS2 CLI command | [`docs/references/cli-commands.md`](../references/cli-commands.md) |
| Write your first node | [`docs/references/node-pattern.md`](../references/node-pattern.md) |
| Understand *why* we use something (Kalman filters, PID, quaternions, udev rules) | the rest of [`docs/concepts/`](.) |
| Read the official ROS2 (Humble) docs | https://docs.ros.org/en/humble/ |
