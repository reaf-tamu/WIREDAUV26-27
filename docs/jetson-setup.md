# Jetson Setup

This document walks through setting up a Jetson Orin Nano from scratch, all the way to having ROS2 Humble installed and ready for this repo. It exists because this process has several non-obvious steps that aren't part of a normal computer setup — this doc is the accumulated knowledge from actually doing it, so the next person doesn't have to rediscover each step the hard way.

**Do this with another team member nearby if it's your first time**, especially the firmware step — it's the part most likely to be confusing on a first attempt.

---

## The big picture, before you start

Getting a Jetson Orin Nano ready involves more steps than "install the OS" because of how NVIDIA structured JetPack releases. Here's the shape of the whole process:

1. Check what's currently on the Jetson.
2. If it's an older JetPack, update its firmware first (a required "bridge" step — explained below).
3. Flash the actual JetPack 6.x operating system onto an SD card.
4. Get the Jetson talking to the internet.
5. Install ROS2 Humble.
6. Clone this repo and run its setup script.

Each of these can go wrong in ways that look unrelated to the actual cause, so read the "why" in each section, not just the commands — it'll save time when something looks broken.

---

## Step 1: Check the current JetPack/firmware version

**JetPack** is NVIDIA's name for the full software bundle that runs on a Jetson (the OS plus NVIDIA-specific drivers and tools). Different JetPack versions are built on different versions of Ubuntu, and — importantly for this project — **ROS2 Humble only has installable packages for Ubuntu 22.04**, which means you need **JetPack 6.x**, not JetPack 5.

Check what's currently installed:
```bash
head -1 /etc/nv_tegra_release
```
This shows a line like `# R35 (release), REVISION: 5.0, ...`. What matters is the `R` number:
- **R35.x** — this is JetPack 5.x (Ubuntu 20.04). You'll need to do Step 2 before you can move to JetPack 6.
- **R36.x** — this is already JetPack 6.x (Ubuntu 22.04). Skip to Step 4.

---

## Step 2: Update the firmware (only needed if you're on JetPack 5)

### Why this step exists
This is the part that's easy to miss and causes real confusion if skipped: the Jetson Orin Nano's bootloader firmware lives in a separate onboard chip (**QSPI** flash), not on the SD card. If you skip straight to flashing a JetPack 6 SD card on a board that's never had this update, **the Jetson won't boot it at all** — you'll get a black screen or a UEFI error, which looks like the SD card image itself is broken, when the real problem is the firmware bridge step below was skipped.

### How to do it
While the Jetson is still running its existing JetPack 5.1.3:
```bash
sudo apt update
sudo apt-get install nvidia-l4t-jetson-orin-nano-qspi-updater
sudo reboot
```
The update applies automatically during that reboot. **There's often no obvious on-screen progress message** — this is normal, don't assume it failed just because nothing visibly happened. Don't power-cycle the board if it seems to be taking a while; let it finish.

Once it's back up, confirm it worked:
```bash
sudo nvbootctrl dump-slots-info
```
You want to see `Current version: 35.5.0` in the output.

**Important: this firmware update is done per physical board**, not per SD card. If your club has multiple Jetsons, each one needs this step done individually before it can boot a JetPack 6 SD card — a JetPack 6 card that boots fine on one updated Jetson will not boot on a different, not-yet-updated one.

---

## Step 3: Flash JetPack 6.x onto an SD card

Once the firmware bridge above is done, flash a JetPack 6.x image (e.g. 6.2.1) onto a microSD card using a tool like Balena Etcher, from a separate computer. Insert the card into the Jetson and boot it — it should now reach a normal Ubuntu 22.04 desktop.

Confirm the version once it's booted:
```bash
head -1 /etc/nv_tegra_release
```
You should now see an `R36.x` line.

---

## Step 4: Get the Jetson talking to the internet

This is where setups quietly go wrong most often, because Jetsons are frequently connected in a way that doesn't automatically include internet access.

### If you're connecting the Jetson directly to a laptop via Ethernet (no router)
This kind of direct link is often set up with **static IPs** — fixed addresses manually assigned to each device, rather than automatically handed out. A static, direct link **has no path to the actual internet** — it can only talk to the one device on the other end of the cable. This is fine for things like SSH, but `apt update` and installing ROS2 will fail with "temporary failure resolving" errors, because there's genuinely no route out to the internet.

**Fix:** connect the Jetson's Ethernet cable to a router with real internet access instead (a lab router, home router, campus wall port) for any step that needs to download something. Note that if the Jetson's network interface was previously configured with a static IP, it may need to be switched to **DHCP** (automatic address assignment) to work properly on a router:
```bash
nmcli connection show                                    # find the connection's name
nmcli connection modify "<connection-name>" ipv4.method auto
nmcli connection up "<connection-name>"
```

### Check the system clock
A Jetson that's just been reflashed can end up with its **system clock** wildly wrong (sometimes reset back to near January 1970). This causes a confusing error where `apt` refuses to trust *any* repository, because it thinks certificates aren't valid yet. Check:
```bash
date
```
If it's clearly wrong, set it manually and save it to the hardware clock so it survives a reboot:
```bash
sudo date -s "24 AUG 2026 12:00:00"    # use the actual current date/time
sudo hwclock -w
```

### Confirm internet access is actually working
```bash
sudo apt update
```
This should complete without any "Temporary failure resolving" errors before moving on.

---

## Step 5: Install ROS2 Humble

Even with working internet access, `apt install ros-humble-desktop` will fail with "Unable to locate package" until the ROS2 package repository itself is added — this is a separate step from just having internet, since `apt` only knows about repos it's been explicitly told about.

```bash
# Make sure Ubuntu's "universe" repository is enabled — ROS2 depends on packages from it
sudo apt install software-properties-common
sudo add-apt-repository universe

sudo apt update && sudo apt install curl -y

# Download and install the official ROS2 apt source configuration
export ROS_APT_SOURCE_VERSION=$(curl -s https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest | grep -F "tag_name" | awk -F\" '{print $4}')
curl -L -o /tmp/ros2-apt-source.deb "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.$(. /etc/os-release && echo $VERSION_CODENAME)_all.deb"
sudo dpkg -i /tmp/ros2-apt-source.deb
```

Now the actual install:
```bash
sudo apt update
sudo apt install ros-humble-desktop
sudo apt install python3-colcon-common-extensions python3-rosdep python3-vcstool
sudo rosdep init && rosdep update
```

This installs a lot of data — let it run rather than assuming it's frozen partway through.

**A note on naming, since it trips people up:** you'll see the word "jammy" appear in this process alongside "humble." These are two separate naming schemes — **Jammy** is the Ubuntu 22.04 release codename, **Humble** is the ROS2 release codename. Seeing both together (e.g. a package named `ros2-apt-source (jammy)`) is expected and correct, not a sign something's mismatched.

---

## Step 6: Set up this repo

Once ROS2 is installed:
```bash
mkdir -p ~/auv_ws/src
cd ~/auv_ws/src
git clone https://github.com/your-club/auv_software.git .
./setup.sh
cd ~/auv_ws
colcon build
```
See the root `README.md` and `docs/architecture-roadmap.md` for what happens from here.

---

## Troubleshooting quick reference

| Symptom | Likely cause | Where to look |
|---|---|---|
| Black screen or UEFI error booting a JetPack 6 SD card | Firmware bridge update (Step 2) was skipped | Step 2 |
| `apt update` fails with "Temporary failure resolving..." | No real internet route (direct static link) | Step 4 |
| `apt update` fails citing a repo "not valid yet" for a huge number of days | System clock is wrong | Step 4 |
| `Unable to locate package ros-humble-desktop` | ROS2 apt repo was never added | Step 5 |
| SSH to a saved IP suddenly stops working | The IP changed (DHCP reassignment) or you're on the wrong subnet | Ping the address first from a plain terminal; check `ip addr` directly on the Jetson if unreachable |
| `ping` returns a reply from a totally different address than the one you pinged | Your computer has no route to that address on any interface and fell back to a default gateway | Check `ipconfig /all` (Windows) or `ip addr` (Linux) for the adapter actually connected to the Jetson |

---

## Where to go next

Once ROS2 and this repo are set up, `docs/architecture-roadmap.md` picks up from here — it covers how the sensors, control loop, and vision system fit together, and the order to build and test them in.
