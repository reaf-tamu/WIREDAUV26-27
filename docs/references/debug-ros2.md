# Debugging ROS2: a command playbook

`docs/reference/cli-commands.md` covers what each command does in general. This doc is organized the other way around: **by symptom** — "here's what's going wrong, here's what to run, here's how to read the result." Everything here is a command we've actually reached for while debugging a real problem on this project, not a hypothetical.

## Start here: the general debugging order

Before jumping to a specific symptom below, this rough sequence has consistently narrowed down problems fastest on this project — work through it top to bottom rather than guessing which layer is broken:

1. **Is the node even running?** → `ros2 node list`
2. **Does the topic exist?** → `ros2 topic list | grep <keyword>`
3. **Is data actually flowing on it?** → `ros2 topic hz <topic>`
4. **Does the content look right?** → `ros2 topic echo <topic> --once`
5. **If hardware's involved: is anything else holding the device open?** → `sudo fuser -v /dev/<device>`

Each step rules out one whole category of explanation before you move to the next — jumping straight to reading source code or guessing at config values tends to take much longer than this.

---

## Symptom: "My node doesn't seem to be running"

```bash
ros2 node list
```
If your node's name isn't in this list, it either never started or it crashed. Check the terminal you launched it from for a `process has died` line — that's the actual crash, usually with a traceback printed just above it.

If it's not clear which terminal/process to look at (e.g. it was started via `ros2 launch` alongside several others), find the log files instead:
```bash
ls -dt ~/.ros/log/*/ | head -1
```
This shows the most recent launch session's log directory. Note: in our experience, this directory has sometimes only contained `launch.log` and not per-node logs — if that's the case, the real error only exists in the terminal's scrollback, not on disk, so don't spend time hunting for a log file that isn't there.

---

## Symptom: "A topic exists but nothing's coming through"

```bash
ros2 topic hz /vectornav/imu
```
If this hangs with no output, or says `does not appear to be published yet`, the publisher side is the problem — go check that node directly, not the subscriber.

```bash
ros2 topic info /vectornav/imu --verbose
```
Shows publisher/subscriber **counts** and their **QoS settings**. Two very different problems look identical from `topic hz` alone:
- **0 publishers** → nothing is actually producing data.
- **1 publisher, but a QoS mismatch** (e.g. one side `BEST_EFFORT`, the other `RELIABLE`) → ROS2 silently refuses to connect them. No error message, just zero messages ever arriving on either end. This is a subtle, easy-to-miss cause — always worth checking QoS on both ends before concluding the publisher itself is broken.

---

## Symptom: "Something might have this serial device already open"

```bash
sudo fuser -v /dev/vectornav
```
Lists every process with that device open. If more than one shows up, that's your problem — two processes reading the same serial port will steal each other's incoming bytes, producing errors like `device reports readiness to read but returned no data`.
```bash
sudo kill -9 <pid>
```
Kill the extra one(s), then confirm it's actually clear before relaunching:
```bash
sudo fuser -v /dev/vectornav
```
(should print nothing)

**Common cause on this project:** a launch attempt that errors out partway through doesn't always cleanly stop every node it had already started — an orphaned process from a *previous, failed* launch is a very easy thing to mistake for a fresh bug. Worth checking this any time a device behaves inconsistently between attempts for no obvious reason.

---

## Symptom: "Is the OS even seeing my USB device correctly?"

```bash
sudo dmesg | tail -20
```
(needs `sudo` — without it you may get `read kernel buffer failed: Operation not permitted` on some systems)

Look for the actual attach/detach events for your device. Things worth noticing:
- A clean `FTDI USB Serial Device converter now attached to ttyUSBx` with nothing alarming right after it → the connection itself is healthy; look elsewhere (software/config) for the problem.
- Repeated attach/detach cycles in quick succession → a flaky physical connection (cable, port, or a power issue), not a software bug.
- `ftdi_sio ttyUSBx: failed to set flow control: -110`, `ftdi_set_termios FAILED`, or anything ending in a similar `-110`/timeout code → this is the kernel failing to talk to the USB device at the hardware/protocol level. Try a different USB port and a different cable before suspecting your code at all — we've hit this exact error and it was resolved purely by swapping hardware, not changing anything in software.

```bash
ls /dev/ttyUSB*
```
Quick check for what serial devices currently exist at all, before digging further into any one of them.

---

## Symptom: "Which physical device is which /dev/ttyUSBx?"

```bash
udevadm info -a -n /dev/ttyUSB0 | grep -E 'ATTRS\{idVendor\}|ATTRS\{idProduct\}|ATTRS\{serial\}'
```
Shows the specific USB device's identifying info. Useful both for writing a new udev rule (see `docs/concepts/udev-rules.md`) and for confirming whether two `/dev/ttyUSBx` entries are actually the same physical device's two channels, or genuinely two separate devices — don't assume; check the serial number field.

---

## Symptom: "My coordinate frame / transform doesn't seem right"

```bash
ros2 run tf2_ros tf2_echo base_link vectornav
```
Prints the actual transform currently being published between two frames — translation, rotation as both quaternion and human-readable roll/pitch/yaw. If this hangs saying `Invalid frame ID ... frame does not exist`, either the transform publisher isn't running, or you've got a typo in one of the frame names — check `ros2 node list` for the expected `static_transform_publisher` (or similarly named) node first.

---

## Symptom: "My node parameters don't seem to match what I set in the launch file"

```bash
ros2 param list /vn100_ascii_node
ros2 param get /vn100_ascii_node port
```
Confirms exactly what value a running node actually has for a given parameter, right now — useful for confirming whether a launch file's override actually took effect, versus the node silently falling back to its coded-in default.

---

## Symptom: "Everything about my ROS2 environment feels wrong" (general sanity check)

```bash
echo $ROS_DISTRO
```
Empty output here explains an enormous range of downstream problems — `rosdep` failing to resolve totally normal dependencies, commands not being found, etc. If empty, `source /opt/ros/humble/setup.bash` (and check it's actually in `~/.bashrc` so this doesn't recur every new terminal).

```bash
groups $USER
```
Confirms whether your user is in the `dialout` group — needed to open serial devices at all, independent of anything else being correctly configured. If `dialout` isn't listed: `sudo usermod -aG dialout $USER`, then log out and back in for it to take effect.

---

## A meta-point worth remembering

More than once on this project, a "software bug" turned out to be a fully orphaned process from a previous crashed launch, a USB cable/port issue, or an environment variable that silently wasn't set — none of which show up by staring harder at the code that's actually failing. When something behaves inconsistently between attempts, or fails in a way that doesn't make sense given the code, it's worth running through this doc's commands before assuming the bug is in the logic you're looking at.
