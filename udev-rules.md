# udev rules & stable device names

## The problem it solves

Plug a USB sensor into the Jetson, and Linux gives it a name like `/dev/ttyUSB0`. Plug in a second one, and it becomes `/dev/ttyUSB1`. This sounds simple until you notice the assignment isn't fixed to the physical device — it's just "whichever order things got detected in." Unplug and replug things, reboot, or plug in a completely unrelated USB device first, and suddenly your VN-100 might be `/dev/ttyUSB1` instead of `/dev/ttyUSB0`, with no warning.

If a launch file or config hardcodes `port: /dev/ttyUSB0`, that config is only correct until the next time the enumeration order shuffles — then it silently points at the wrong device, or no device at all. This isn't a hypothetical: we hit exactly this while bringing up the VN-100 (see `docs/sensors/vn100.md`), where the same physical sensor showed up as `/dev/ttyUSB0` in one session and `/dev/ttyUSB1` in the next.

**udev rules fix this** by giving a specific physical device a fixed, predictable name that never changes, no matter what order things get plugged in.

## What udev actually is

`udev` is the part of Linux responsible for noticing when hardware is plugged in or removed, and creating the corresponding device file in `/dev/` (like `/dev/ttyUSB0`). It does this automatically, using built-in rules that ship with the OS — but you can also add your own rules that tell it "when you see *this specific device*, also do *this extra thing*." That's what we're doing here: adding one extra instruction that says "when you see this exact sensor, also create a permanent, friendly-named shortcut to it."

## What a symlink actually is

A **symlink** (symbolic link) is just a shortcut — a name that points to another file, the same way a shortcut icon on a desktop points to the real program. `/dev/vectornav` isn't a second, separate device; it's a pointer that says "whatever `/dev/vectornav` is asked for, actually go use this other file instead." When udev creates the symlink, it points it at whatever the real device currently is (`/dev/ttyUSB0`, `/dev/ttyUSB1`, whatever it happens to be *right now*) — and critically, **udev re-points that symlink automatically every time the device is reconnected**, even if the underlying `/dev/ttyUSBx` number changes. Our code never has to know or care what the raw number is; it just always asks for `/dev/vectornav` and gets routed correctly.

You can see this yourself:
```bash
ls -l /dev/vectornav
```
This shows something like:
```
lrwxrwxrwx 1 root root 7 Aug 26 13:45 /dev/vectornav -> ttyUSB0
```
That `-> ttyUSB0` is the symlink in action — right now, `/dev/vectornav` happens to point at `ttyUSB0`, but that target can and does change across reboots/replugs. The fixed part is the *name* `/dev/vectornav`, not the number it currently resolves to.

## Why we key the rule on the serial number, not just vendor/product ID

Every USB device reports a **vendor ID** and **product ID** — numbers identifying the manufacturer and model of chip. A naive udev rule matches on just these two. The problem: many devices, including our own VN-100's USB breakout board, use a common, mass-produced USB-to-serial chip (in our case, an FTDI chip) that plenty of *other* devices also use. If we matched only on vendor/product ID, the rule would match *any* device using that same chip — including, in our own case, the sensor's own second, unrelated internal port (see `docs/sensors/vn100.md` section 4), which would create an ambiguous, conflicting symlink.

The fix is matching on the device's **serial number** as well — a value that's supposed to be unique to that one specific physical unit, not just its chip model. This is why our actual rule includes all three:
```
SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="6001", ATTRS{serial}=="FTY5H4F5", SYMLINK+="vectornav"
```
- `idVendor`/`idProduct` narrow it down to "an FTDI chip of this exact model"
- `ATTRS{serial}` narrows it down further to "this *one* physical chip, not any other FTDI device that happens to share the same model"

Without the serial number here, this rule would have matched both of the VN-100 breakout's two ports (and potentially any other FTDI-based sensor on the bench at the same time) — which is exactly the ambiguity that made our sensor identification confusing in the first place.

## How to set this up for a new sensor, step by step

### 1. Plug in the sensor and find its raw device name

```bash
ls /dev/ttyUSB*
```
Note which one is new (unplug/replug and re-run this if multiple are already present and you're not sure which is the new one).

### 2. Confirm it's actually the right device before going further

Don't assume — test it directly first (e.g. with `minicom -D /dev/ttyUSBx -b <baud>` for a serial sensor) to confirm real, expected data is coming through on that specific port. Skipping this step means you could build a permanent rule pointing at the wrong device entirely.

### 3. Get the device's unique identifying attributes

```bash
udevadm info -a -n /dev/ttyUSBx | grep -E 'ATTRS\{idVendor\}|ATTRS\{idProduct\}|ATTRS\{serial\}'
```
This prints (potentially several sets of) vendor ID, product ID, and serial number as udev walks up the device's hierarchy. You want the **first** set that appears — that's the actual USB device itself, not a parent hub or unrelated ancestor further up the chain.

**If the serial number field is missing or blank:** not every device exposes one. In that case, matching on vendor/product ID alone is the fallback — but be aware this won't distinguish between two identical sensors, or (as in our case) two ports sharing the same chip. If you hit this, flag it — there are more advanced udev tricks (matching by physical USB port path instead of serial number) that can help, but they're outside the scope of this doc.

### 4. Write the rule

```bash
sudo nano /etc/udev/rules.d/99-<sensor-name>.rules
```
```
SUBSYSTEM=="tty", ATTRS{idVendor}=="<vendor>", ATTRS{idProduct}=="<product>", ATTRS{serial}=="<serial>", SYMLINK+="<sensor-name>"
```
Pick a clear, descriptive `<sensor-name>` — this becomes the permanent name everyone on the team will use in configs and launch files (e.g. `vectornav`, `ping_sonar`, `pressure_sensor`). The `99-` filename prefix just controls the order udev processes rule files in; `99` runs late, which is the normal convention for custom rules like this so they apply after any built-in system rules.

### 5. Apply the rule without needing a reboot

```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```
If the symlink doesn't appear right away, a full unplug/replug of the device is the most reliable way to force udev to re-evaluate it — `udevadm trigger` alone can sometimes replay a weaker "device changed" event rather than a full "device added" one.

### 6. Verify it

```bash
ls -l /dev/<sensor-name>
```
Confirm it exists and points at a real `ttyUSBx`. Then unplug and replug the actual device and check again — the symlink should reappear pointing at whatever `ttyUSBx` number it lands on this time, proving the whole point of doing this in the first place.

### 7. Use the stable name everywhere, never the raw number

Update the sensor's driver config/launch file to reference `/dev/<sensor-name>`, not `/dev/ttyUSBx`. This is the actual payoff — from this point on, that config is correct forever, regardless of what order devices get plugged in on any future boot.

## A note on permissions (a separate, related issue)

Being able to *open* a serial device at all (independent of naming) requires your user account to be in the `dialout` group:
```bash
groups $USER
sudo usermod -aG dialout $USER
```
(log out and back in, or reboot, for group membership changes to take effect)

This is a separate concern from the naming problem this doc covers — a udev rule can exist and work perfectly while a permissions issue still blocks your user from actually reading the device. If a sensor's symlink resolves correctly but code still can't open it, check this first.

## Resources to learn more

- **[Clearpath Robotics: Udev Rules (ROS)](https://docs.clearpathrobotics.com/docs/ros1noetic/ros/ros/tutorials/ros101/intermediate/udev_rules/)** — written specifically for robotics/ROS use cases very close to ours, including the exact "multiple devices sharing a common USB-to-serial chip" problem this doc covers.
- **[Downtown Doug Brown: Linux udev rules](https://www.downtowndougbrown.com/2014/03/linux-udev-rules/)** — a clear, beginner-friendly walkthrough of udev rule syntax in general, useful if you want to go beyond the copy-paste recipe above and actually understand every field.
