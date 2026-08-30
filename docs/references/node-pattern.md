# The standard ROS2 node pattern

Every node in this repo — `vn100_ascii_node.py`, `thruster_allocator_node.py`, `thruster_interface_node.py`, `attitude_control_node.py` — follows the same overall shape, both in how the node's class is built and in how its `main()` function runs it. Once this pattern is familiar, reading (or writing) a new node gets a lot faster, since most of it is boilerplate you've already seen.

This doc walks through *why* each piece is there, not just what it does — the goal is that this stops looking like a template to copy-paste and starts making sense as a sequence of real, necessary steps.

## The class: what goes in `__init__`

Every node is a Python class that inherits from `Node` (from `rclpy.node`). Here's the shape, using `attitude_control_node.py` as the running example:

```python
class AttitudeControlNode(Node):
    def __init__(self):
        super().__init__('attitude_control_node')
        ...
```

**`super().__init__('attitude_control_node')`** — this is the very first line of every node's `__init__`, no exceptions. It hands control up to `Node`'s own constructor (the parent class we're inheriting from), passing along the node's name. That name is what shows up when you run `ros2 node list` — it's how ROS2 and other tools refer to this specific running process. Skipping this line, or putting other code before it, means the node isn't actually registered with ROS2 yet, and nothing below will work correctly.

From here, `__init__` is where a node declares everything it needs to do its job:

**Subscriptions** — how a node receives data from topics:
```python
self.create_subscription(Odometry, '/odometry/filtered', self.odom_callback, 10)
```
Four things here: the message type (`Odometry`), the topic name, the function to call every time a new message arrives (`self.odom_callback` — note it's passed as a reference, not called directly), and a queue size (`10` — how many unprocessed messages to hold onto if they arrive faster than they're being handled).

**Publishers** — how a node sends data out:
```python
self.wrench_pub = self.create_publisher(Wrench, '/auv/wrench', 10)
```
Saved as `self.wrench_pub` because, unlike a subscription (which just needs to exist once, in the background), you'll actually call `.publish()` on this later, elsewhere in the class — so you need to keep a reference to it.

**Timers** — for anything that should run on a schedule rather than only in response to incoming messages:
```python
self.timer = self.create_timer(0.05, self.control_loop)
```
This calls `self.control_loop` every 0.05 seconds (20 Hz), regardless of whether new sensor data has arrived. `attitude_control_node.py` uses this instead of running the control loop directly inside `odom_callback` specifically so `dt` (time between control loop iterations) stays well-defined and consistent, even if a sensor message is briefly late or dropped.

**Parameters** — runtime-configurable values with defaults, overridable from a launch file without touching code:
```python
self.declare_parameter('port', '/dev/vectornav')
port = self.get_parameter('port').value
```
See `docs/sensors/vn100.md` and `vn100.launch.py` for this in action — it's how the same node code works with different settings without being edited.

**Plain instance variables** — ordinary Python state a node needs to remember between calls, like `self.current_yaw = 0.0` in `attitude_control_node.py`. Nothing ROS-specific here, just normal object state.

## The callback functions

Anything passed to `create_subscription` or `create_timer` needs to be an actual method on the class, defined separately from `__init__`:

```python
def odom_callback(self, msg: Odometry):
    self.current_yaw = quaternion_to_yaw(msg.pose.pose.orientation)
    self.current_depth = msg.pose.pose.position.z
```

The key thing to understand: **you never call these yourself.** `rclpy.spin()` (covered below) is what actually invokes them, automatically, whenever a new message arrives or a timer fires. Your job in `__init__` is just to register them; ROS2's event loop is what runs them.

## `main()`: the five-step pattern

Every node file ends with a `main()` function shaped like this:

```python
def main(args=None):
    rclpy.init(args=args)      # 1
    node = AttitudeControlNode()  # 2
    try:
        rclpy.spin(node)       # 3
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()    # 4
        rclpy.shutdown()       # 5


if __name__ == '__main__':
    main()
```

**1. `rclpy.init(args=args)`** — starts up ROS2's underlying communication system. This has to happen before anything else ROS2-related — before a node is even created. `args=args` passes along command-line arguments so `ros2 launch`'s parameter overrides and remappings actually reach the node.

**2. `node = AttitudeControlNode()`** — this is where `__init__` (everything covered above) actually runs, creating the node and setting up all its subscriptions/publishers/timers. Note this only works *because* `rclpy.init()` already ran — creating a node before initializing ROS2 would fail.

**3. `rclpy.spin(node)`** — this is the part that actually keeps the program alive and doing anything. `spin()` runs an event loop that waits for incoming messages, timer ticks, etc., and calls the corresponding callback each time one happens. Without this call, the node would be created and then the program would just... end, having never actually processed anything. This call blocks (doesn't return) until the node is told to stop, which is normally via `Ctrl+C`.

**Why the `try`/`except KeyboardInterrupt`** — `Ctrl+C` raises a `KeyboardInterrupt` inside `spin()`. Catching it here means the program exits cleanly instead of printing a scary-looking Python traceback for what is actually a completely normal, expected way to stop a node.

**4 & 5. `node.destroy_node()` then `rclpy.shutdown()`** — cleanup, in the `finally` block so it runs whether the node exited normally or via `Ctrl+C`. This mirrors steps 1 and 2 in reverse: `destroy_node()` cleans up this specific node's resources, `shutdown()` tears down the shared ROS2 communication system entirely. **Order and symmetry matter here** — we hit a real bug once from calling `rclpy.shutdown()` a second time after it had already run (see `docs/sensors/vn100.md`'s change log); keeping this pattern exactly as shown, rather than improvising it, avoids that class of mistake.

## Using the logger

Every node has a built-in logger, accessed via `self.get_logger()` — this is almost always better than a plain Python `print()` inside a node, for a few concrete reasons: log messages automatically get tagged with which node they came from (useful once several nodes are running via `ros2 launch` and everything's interleaved in one terminal), they come with severity levels so you can tell "just informational" apart from "something's actually wrong" at a glance, and tools like `ros2 launch` format them consistently (you've seen this as the `[INFO]`/`[WARN]`/`[ERROR]` prefixes in launch output throughout this whole project).

```python
self.get_logger().info(f'Opening {port} @ {baud}')
```

The common severity levels, roughly in order of urgency:
- **`.debug(...)`** — verbose detail, useful while actively developing, usually too noisy to leave on by default.
- **`.info(...)`** — normal status updates. This is what you've seen constantly in launch output, like `Connected to /dev/vectornav @ 115200 baud`.
- **`.warn(...)`** — something's off but not necessarily broken; worth a human's attention without stopping anything.
- **`.error(...)`** — something failed. We use this pattern in `vn100_ascii_node.py`'s `read_loop()`: `self.get_logger().error(f'Serial read failed: {e}')`.

A good rule of thumb from this project's own debugging sessions: the more informative a node's logging is at startup (confirming what port/topic/parameter it actually ended up using, not just "started successfully"), the less time gets spent later guessing why something silently isn't working — several of the VN-100 debugging sessions would have been faster with a bit more `.info()` logging up front confirming exactly what the node believed its own configuration to be.

## Putting it all together

The full shape, once you can see the whole thing at once:

```
class MyNode(Node):
    def __init__(self):
        super().__init__('my_node')      # register with ROS2
        # ... subscriptions, publishers, timers, parameters go here ...

    def some_callback(self, msg):
        # ... runs automatically when triggered ...

def main(args=None):
    rclpy.init(args=args)                # start ROS2
    node = MyNode()                      # build the node
    try:
        rclpy.spin(node)                 # run forever, reacting to events
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()              # clean up
        rclpy.shutdown()                 # stop ROS2

if __name__ == '__main__':
    main()
```

Every custom node in this repo is a variation on this same skeleton — different subscriptions, different logic inside the callbacks, but the same overall shape holding it together.
