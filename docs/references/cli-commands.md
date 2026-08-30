# ROS2 CLI reference

A quick-lookup reference for the terminal commands you'll actually type while working on this project. For *why* topics/nodes/services exist conceptually, see the README's glossary; this doc is about the commands themselves.

## The general format

Almost every ROS2 command follows the same shape:

```
ros2 <command> <verb> [arguments]
```

- **`ros2`** — the base program. Everything ROS2-related on the command line starts with this.
- **`<command>`** — which *category* of thing you're working with: `topic`, `node`, `launch`, `run`, `pkg`, `param`, etc.
- **`<verb>`** — what you want to *do* with that category: `list`, `echo`, `info`, `hz`...
- **`[arguments]`** — usually a specific topic/node/package name, plus optional flags.

So `ros2 topic echo /vectornav/imu` breaks down as: category = `topic`, verb = `echo`, argument = `/vectornav/imu`. Once this pattern clicks, most new commands are guessable — if you want to know something about nodes, it almost certainly starts with `ros2 node ...`.

**Before any of these will work**, your terminal needs ROS2's environment loaded. If a command fails with something like "command not found" or complains it can't find message types, check:
```bash
echo $ROS_DISTRO
```
If that's empty, see `docs/jetson-setup.md` for the fix (should already be permanent in `~/.bashrc` on the team Jetson, but worth knowing what's going on if it ever isn't).

For anything running from this repo specifically (our own packages, custom message types), you also need to have sourced this workspace's build output — every terminal you use for `ros2 run`/`ros2 launch` on our packages should start with:
```bash
source ~/auv_ws/install/setup.bash
```

---

## `ros2 topic` — inspecting the data flowing between nodes

| Command | What it does |
|---|---|
| `ros2 topic list` | Lists every topic currently active. |
| `ros2 topic echo /vectornav/imu` | Prints every message on that topic, live, as it arrives. `Ctrl+C` to stop. |
| `ros2 topic echo /vectornav/imu --once` | Same, but grabs just one message and stops — useful for a quick "is this the right shape/type" check without your terminal filling with scrolling text. |
| `ros2 topic hz /vectornav/imu` | Reports how *often* messages are arriving (e.g. "39.0 Hz"), without showing their content. Good first check when debugging "is data actually flowing at all" — it directly answers that without the noise of `echo`. |
| `ros2 topic info /vectornav/imu --verbose` | Shows the message type, how many publishers/subscribers are connected, and their QoS settings. The `--verbose` flag is what adds the QoS details — without it, you just get the basic counts. |
| `ros2 topic pub /auv/wrench geometry_msgs/msg/Wrench "{force: {x: 0.5}}"` | Manually publishes a single message onto a topic, useful for testing a node without needing whatever normally produces that data (e.g. testing the thruster allocator without a real PID loop running yet). |
| `ros2 topic pub ... --once` | Same as above, but sends exactly one message and exits, instead of publishing repeatedly forever (the default behavior of `pub` without this flag). |

**A pattern worth internalizing:** `list` tells you *what exists*, `info`/`hz` tell you *about* something that exists, `echo` shows you the *actual content*. When debugging "why isn't my node getting data," that's usually the right order to check them in — confirm the topic exists first, then confirm something's publishing to it, then look at the content.

---

## `ros2 node` — inspecting running nodes

| Command | What it does |
|---|---|
| `ros2 node list` | Lists every node currently running. Good first check after a launch — if a node you expected isn't in this list, it either failed to start or crashed silently. |
| `ros2 node info /vn100_ascii_node` | Shows everything about a specific node: what topics it publishes/subscribes to, what services/actions it offers. Useful for "what is this node actually doing" without reading its source. |

---

## `ros2 launch` — starting a set of nodes together

```
ros2 launch <package_name> <launch_file_name>
```
Example:
```bash
ros2 launch auv_vn100 vn100.launch.py
```
Launch files start one or more nodes together with a shared configuration, instead of running each with a separate `ros2 run` command in separate terminals. Almost everything we bring up (a single sensor, or the whole `auv_bringup` stack) goes through `ros2 launch`, not `ros2 run`, once there's more than one node involved.

**Reading launch output:** each line is prefixed with which process it came from, e.g. `[vn100_ascii_node-1]` — the number is just launch's internal counter for that process, not meaningful on its own. `[INFO]` lines are normal status updates; `[WARN]` is worth a glance but usually not fatal; `[ERROR]` followed by `process has died` means that specific node crashed — the other nodes in the same launch keep running unless they depended on the one that died.

---

## `ros2 run` — starting a single node directly

```
ros2 run <package_name> <executable_name>
```
Example:
```bash
ros2 run auv_control thruster_allocator_node
```
Use this instead of `ros2 launch` when you want just *one* node running, usually for isolated testing (like testing the allocator alone with a manually published `ros2 topic pub`, without the rest of the stack running).

---

## `ros2 pkg` — inspecting packages themselves

| Command | What it does |
|---|---|
| `ros2 pkg list` | Lists every ROS2 package currently available in your environment (built workspace packages + everything from the system install). |
| `ros2 pkg prefix vectornav` | Prints the install path a package's built files actually live in. Useful for finding a package's real launch/config files on disk when you're not sure of the exact filename — pair with `ls`, e.g. `ls $(ros2 pkg prefix vectornav)/share/vectornav/launch`. |

---

## `ros2 param` — reading/setting a running node's parameters

| Command | What it does |
|---|---|
| `ros2 param list /vn100_ascii_node` | Shows every parameter that node has declared (e.g. `port`, `baud`, `frame_id`). |
| `ros2 param get /vn100_ascii_node port` | Shows the current value of one specific parameter. |

Parameters are usually set once at launch time via the launch file, not changed live, but these commands are handy for confirming a launch file's parameter override actually took effect.

---

## `colcon build` — building the workspace

Not a `ros2` command — `colcon` is the separate build tool ROS2 projects use, always run from the **workspace root** (`~/auv_ws`, one level above `src/`), never from inside `src/`.

| Command | What it does |
|---|---|
| `colcon build` | Builds every package in `src/`. |
| `colcon build --packages-select auv_vn100` | Builds only the named package(s) — much faster when you've only changed one thing, instead of waiting on every package to rebuild. |

**After any build**, you need to re-source before the changes are usable in that terminal:
```bash
source ~/auv_ws/install/setup.bash
```
This is a very common "why isn't my change showing up" trap — the build succeeded, but the currently-open terminal is still pointing at the old build output until re-sourced. Opening a fresh terminal after a build works too, as long as `source /opt/ros/humble/setup.bash` and this workspace's `install/setup.bash` are both in your shell's normal startup (check `~/.bashrc`).

**Reading build output:** a clean build ends with a `Summary:` line listing how many packages finished successfully. A failed package shows as `Failed <<< package_name` with the actual error just above it (often a Python traceback for our packages, or a CMake error for C++ ones); anything that depended on the failed package shows as `Aborted <<<` — that's not a separate bug, it's just colcon refusing to build something on top of a broken dependency.

---

## `rosdep` — installing a package's system dependencies

```bash
rosdep install --from-paths src --ignore-src -r -y
```
Run from the workspace root, same as `colcon build`. Reads every package's `package.xml` and installs whatever system packages they declared as dependencies (e.g. `robot_localization`, `python3-serial`) via `apt`. Needed after cloning the repo fresh, or after adding a new dependency to a `package.xml`. Requires `ROS_DISTRO` to be set (see the top of this doc) or it'll fail to resolve almost everything.

---

## The standard node `main()` pattern

Every one of our nodes' `main()` functions follows the same five-step shape — worth recognizing once, since it shows up everywhere:

```python
def main(args=None):
    rclpy.init(args=args)      # 1. start up ROS2's communication system
    node = SomeNode()          # 2. create the node (only works after step 1)
    try:
        rclpy.spin(node)       # 3. keep it alive, running callbacks, until interrupted
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()    # 4. clean up the node
        rclpy.shutdown()       # 5. tear down ROS2's communication system
```

- **`rclpy.init()`** must run before anything else ROS2-related — creating a node, publishing, subscribing, none of it works until this has run once.
- **`rclpy.spin(node)`** is what actually keeps the program running and responsive — it's what calls your subscription callbacks, timer callbacks, etc., in a loop, until the program is interrupted (`Ctrl+C`) or told to stop.
- **`destroy_node()` / `shutdown()`** are cleanup, mirroring `init()`/creation in reverse. Skipping these, or calling `shutdown()` twice, can throw errors on exit (we hit exactly this once — see `docs/sensors/vn100.md`'s change history) — not usually dangerous, but worth keeping the pattern intact rather than improvising it.

---

## A useful debugging sequence

When something's not working and you're not sure where to start, this is roughly the order we've reached for repeatedly on this project:

1. `ros2 node list` — is the node even running?
2. `ros2 topic list | grep <keyword>` — does the topic exist?
3. `ros2 topic hz <topic>` — is data actually flowing?
4. `ros2 topic echo <topic> --once` — does the content look right?
5. If a device/serial issue is suspected: `sudo fuser -v /dev/<device>` — is something else already holding the port open?

Working through these roughly in order usually narrows down "is this a launch problem, a data problem, or a hardware problem" faster than jumping straight to reading source code.

