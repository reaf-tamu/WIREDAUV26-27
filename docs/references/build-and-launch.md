# Building and launching

This covers two separate tools that get used together constantly but do very different jobs: **`colcon build`** turns your source code into something ROS2 can actually run, and **`ros2 launch`** starts a group of nodes together. Nearly every error we've hit on this project traces back to a misunderstanding of one of these two steps — this doc collects the real ones, not hypothetical examples.

---

## Part 1: `colcon build`

### What it actually is

`colcon` is the build tool ROS2 workspaces use — it's a separate program from `ros2` itself (notice it's just `colcon build`, not `ros2 build`). It looks at every package inside your workspace's `src/` folder, figures out what kind of package each one is (Python vs. C++, mainly), and produces a built, runnable version of each one inside an `install/` folder alongside `src/`.

### Why we need this step at all

It might seem like Python code should just... run, without a "build" step. Two real reasons this isn't the case in a ROS2 workspace:

1. **Custom message types need code generated for them.** When you write a `.msg` file (like `auv_msgs/msg/Setpoint.msg` or `ThrusterCommands.msg`), that's just a plain-text description of some fields — it isn't Python or C++ code yet. `colcon build` is what runs the tool (`rosidl`) that turns that description into real, usable Python classes you can import and use in your nodes.
2. **Packages need to be "installed" into a place ROS2's tools know to look.** Even pure-Python packages get copied into `install/<package_name>/` in a specific structure, with metadata files that let commands like `ros2 run` and `ros2 launch` find them by name, and let `FindPackageShare(...)` (used constantly in our launch files) locate their launch/config files.

Skipping the build step, or forgetting to rebuild after a change, is one of the most common sources of "why isn't my change showing up" confusion — the running code is whatever was last built, not whatever's currently saved in `src/`.

### How to use it

Always run from the **workspace root** (`~/auv_ws`), never from inside `src/`:
```bash
cd ~/auv_ws
colcon build
```
This builds every package. For a faster, targeted rebuild after changing just one package:
```bash
colcon build --packages-select auv_vn100
```

**After every build, re-source before the change is usable in that terminal:**
```bash
source ~/auv_ws/install/setup.bash
```
This has bitten us before — the build can succeed perfectly, but an already-open terminal keeps using the old build output until it's re-sourced (or you open a fresh terminal, assuming `.bashrc` sources it automatically on startup).

### Reading `colcon build` output

A clean, successful build ends with something like:
```
Summary: 5 packages finished [7.72s]
```
That's the number to look for — if it matches how many packages you expected to build, you're done.

A failure looks like this instead:
```
Failed   <<< auv_bringup [0.13s, exited with code 1]
Aborted  <<< auv_localization [0.13s]
Summary: 0 packages finished [4.00s]
  1 package failed: auv_bringup
  5 packages aborted: auv_localization auv_msgs ...
```
**`Failed` and `Aborted` mean different things.** `Failed` is the package that actually broke — the real error is printed just above this line, usually as a Python traceback (for our packages) or a CMake error message. `Aborted` means that package never even got a chance to build, because colcon stopped everything once a `Failed` package showed up. **Always scroll up to find the `Failed` package's actual error — don't waste time investigating an `Aborted` package, since it's very likely completely fine on its own.**

### Real `colcon build` errors we've hit on this project

| Error | What it actually means | Fix |
|---|---|---|
| `can't open file '.../auv_bringup/setup.py': No such file or directory` | An `ament_python` package is missing required files (`setup.py`, `setup.cfg`, a `resource/<pkg>` marker, and the inner Python module folder) — a `package.xml` alone isn't enough. | Create the missing files — see `docs/reference/node-pattern.md` for what a complete package needs, or copy the structure from an existing working package like `auv_vn100`. |
| `CMake Error ... Could not find a package configuration file provided by "ZED"` | The package depends on a proprietary SDK (the ZED camera's SDK) that isn't installed on this machine, and can't be pulled in via `rosdep`/apt. | If you're not working on vision right now, skip the package entirely: `touch <package_folder>/COLCON_IGNORE`. Only install the real SDK when you're actually ready for that stage. |
| `error: package directory 'ping_sonar_ros/ping-python/brping' does not exist` | The package uses a git submodule that didn't get pulled in automatically by a plain clone/`vcs import`. | `cd` into that package's repo and run `git submodule update --init --recursive`. |
| `ModuleNotFoundError: No module named 'serial'` (or similar) | A Python dependency declared in `package.xml` was never actually installed on the system — often because `rosdep install` was run before `ROS_DISTRO` was set, so it silently failed to resolve everything. | Install directly via apt (`sudo apt install python3-serial`), and re-run a full `rosdep install --from-paths src --ignore-src -r -y` from the workspace root to catch anything else that might have been missed the same way. |
| `Sequence should be of same type. Value type 'integer' do not belong` (from a node crashing at launch, not build, but caused by a config file `colcon build` installed) | A YAML config file mixes types in one list — e.g. a bare `0` next to `0.05` in the same array. ROS2's parameter parser requires every element in a list to be the same type. | Make every number in the list consistent — if any value is a decimal, every value in that same list needs a decimal point too (`0.0`, not `0`). |

---

## Part 2: `ros2 launch`

### What it actually is

A **launch file** (always a `.py` file ending in `.launch.py` by convention, though the name itself doesn't matter to ROS2 — the file *content* defines a `generate_launch_description()` function that Python calls) describes a group of nodes to start together, often with their own specific parameters, remappings, or conditions.

### Why we need this instead of just running nodes directly

You *can* start a single node directly with `ros2 run <package> <executable>` — and that's genuinely the right tool when you're testing one node in isolation. But almost nothing on this vehicle runs as just one node. `auv_bringup`'s `bringup.launch.py`, for example, starts the VN-100 driver, the ping sonar, the static transform, and the EKF — all together, in one command, instead of you opening four separate terminals and typing four separate `ros2 run` commands in the right order every single time. Launch files also let one launch file *include* another (see how `bringup.launch.py` includes `auv_vn100`'s own `vn100.launch.py` via `IncludeLaunchDescription`), so each package can define how to start itself, and a higher-level launch file just assembles those pieces rather than duplicating their configuration.

### How to use it

```
ros2 launch <package_name> <launch_file_name>
```
```bash
ros2 launch auv_bringup bringup.launch.py
```

Not sure what launch files a package actually has? Find its installed location and look:
```bash
ros2 pkg prefix <package_name>
ls $(ros2 pkg prefix <package_name>)/share/<package_name>/launch
```
This is worth doing rather than guessing a filename — we've hit real bugs from assuming a driver's launch file was named a certain way when it wasn't.

### Reading `ros2 launch` output

Every line is prefixed with which process it came from:
```
[vn100_ascii_node-1] [INFO] [1787762482.147190631] [vn100_ascii_node]: Opening /dev/vectornav @ 115200
```
- `[vn100_ascii_node-1]` — launch's own label for this process (the number is just an internal counter, not meaningful by itself).
- `[INFO]` / `[WARN]` / `[ERROR]` — the log severity (see `docs/reference/node-pattern.md`'s logger section). `INFO` is routine, `WARN` deserves a glance, `ERROR` usually means something actually broke.
- `[vn100_ascii_node]` (second occurrence) — the actual ROS2 node name, which can differ from the process label if a node's name doesn't match its executable name.

**A node crashing shows up like this:**
```
[ERROR] [ekf_node-6]: process has died [pid 10922, exit code -6, cmd '...']
```
The nodes *other than* the one that crashed keep running — a `ros2 launch` command doesn't stop just because one node in it died. If you expect all your data flowing and something's missing, `ros2 node list` will confirm whether the node you need actually survived.

### Real `ros2 launch` errors we've hit on this project

| Error | What it actually means | Fix |
|---|---|---|
| `package 'zed_wrapper' not found` | The launch file references a package that was never built — often because it's intentionally `COLCON_IGNORE`d (see the build table above), but the launch file still tries to include it. | Comment out that specific `IncludeLaunchDescription(...)` block (and its entry in the final `return LaunchDescription([...])` list) until the package is actually built. |
| `Failed to parse global arguments ... Couldn't parse params file` | A node's YAML config file has a real syntax/type problem (see the mixed-integer/float example above) — the node crashes immediately on startup, before doing anything else. | Fix the YAML, rebuild that package, relaunch. |
| `ModuleNotFoundError: No module named 'brping'` (or similar, but happening at *launch* time rather than build time) | The Python module technically exists on disk, but isn't actually on Python's import search path — common with packages that bundle an external library as a subfolder rather than a proper installed dependency. | Add the specific folder to `PYTHONPATH` (see `docs/sensors/vn100.md`'s troubleshooting section for a worked example with `ping_sonar_ros`). |
| `Failed to initialize <sensor>!` right after `Opening /dev/ttyUSBx...` | The node started and opened the serial port, but the actual hardware isn't responding — usually means the sensor isn't powered/connected right now, not a code bug. | Check the physical connection before debugging the software further. |
| `Serial read failed: device reports readiness to read but returned no data` | Usually port contention — more than one process has the same serial device open at once, often an orphaned node left running from a previous launch attempt that errored out partway through. | `sudo fuser -v /dev/<device>` to see every process holding it open, `sudo kill -9 <pid>` on any extras, then relaunch. |
| `RCLError: failed to shutdown: rcl_shutdown already called` | A node's own shutdown code called `rclpy.shutdown()` more than once (e.g. from double-handling `Ctrl+C`). Cosmetic — happens *after* the node's real work is already done — but worth fixing since it clutters output. | Guard the shutdown call: `if rclpy.ok(): rclpy.shutdown()`. |

### A general debugging habit worth having

After any launch attempt that errors out partway through — even if you fix the error and relaunch right away — it's worth a quick `sudo fuser -v /dev/<any serial device involved>` before trying again. A partial launch failure doesn't always clean up every node it started, and an orphaned process silently holding a port open is a very easy thing to lose an hour chasing as if it were a "real" bug.
