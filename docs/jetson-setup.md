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
7. Set up PyTorch and torchvision for the vision node (Jetson only, and only if you're working on vision).

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

**If you'll be running the vision node:** the PyTorch setup in Step 7 is only verified on **JetPack 6.0**. NVIDIA's PyTorch wheels are built for one specific JetPack version, so a newer JetPack needs a different wheel than the one listed there.

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
git clone https://github.com/reaf-tamu/WIREDAUV26-27.git .
./setup.sh
cd ~/auv_ws
colcon build
```
On a Jetson, `setup.sh` tells rosdep to skip `yolo_ros`'s pip packages (`python3-torchvision-pip` and `python3-ultralytics-pip`) — installing them would replace NVIDIA's PyTorch with a generic build that can't use the GPU. At the end it checks PyTorch, torchvision and Ultralytics. Until you've done Step 7 it prints a warning there; that's expected, and nothing outside the vision node needs them.

See the root `README.md` and `docs/architecture-roadmap.md` for what happens from here.

---

## Step 7: Set up PyTorch and torchvision for the vision node (Jetson only)

> **Status (October 16, 2026):** NVIDIA's PyTorch is installed and GPU-verified on the team's Jetson. The torchvision 0.19.0 source build is in progress and hasn't been verified yet. Update this note once the verify step below passes.

Only the vision node (`yolo_ros`) needs this step. Everything else in the repo builds and runs without it, so skip it if you aren't working on vision.

### Why this step exists
`yolo_ros` runs Ultralytics YOLO, which needs PyTorch and torchvision. `colcon build` succeeds without them, so a missing install only shows up when the node launches. And a normal `pip install torch torchvision` doesn't work on the Jetson: it pulls generic CUDA wheels that can't use the Jetson's GPU, so `torch.cuda.is_available()` returns `False`. NVIDIA publishes a Jetson-specific PyTorch wheel, but **no matching torchvision wheel**, so torchvision has to be built from source against that exact PyTorch.

**Why `yolo_ros` is pinned to 4.7.1:** `dependencies.repos` pins it to release 4.7.1, the last Python/Ultralytics version. On October 6, 2026, `yolo_ros`'s `main` branch was rewritten as a C++/ONNX Runtime node that doesn't use PyTorch at all, so this step only applies to 4.7.1.

These steps are for **JetPack 6.0 (L4T R36.3, CUDA 12.2)** with Python 3.10. Run every command **on the Jetson** — over SSH (`ssh <user>@<jetson-ip>`) or in a terminal on its desktop — not on your laptop.

### Check the Jetson first
Don't install or uninstall anything until you've looked at what's already there:
```bash
python3 -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.version.cuda)"
python3 -m pip list | grep -i -E "torch|nvidia|cuda|triton|numpy|setuptools"
nvcc --version
df -h /home
free -h
```
What to look for:
- **PyTorch** should print `2.4.0a0+07cecf4168.nv24.05 True 12.2`. If it's missing or prints `False`, install NVIDIA's wheel (next section).
- **`nvcc: command not found`** usually just means CUDA isn't on your `PATH`. JetPack installs it under `/usr/local/cuda`, so add `export PATH=/usr/local/cuda/bin:$PATH` to `~/.bashrc` and open a new terminal.
- **setuptools** must be below 80, or `colcon build` breaks. `setup.sh` pins it.
- **numpy** must be below 2. PyTorch 2.4 was built against numpy 1.x.
- **Leftovers from earlier failed installs** (`nvidia-*-cu13`, `cuda-toolkit`, `triton`) may show up in `~/.local`. Don't remove them based on their names alone — it hasn't been checked whether they interfere.
- **Disk and memory:** the torchvision build takes hours, so make sure `df` and `free` show room before starting it.

### Install NVIDIA's PyTorch wheel (skip if the check above passed)
```bash
python3 -m pip install --user "https://developer.download.nvidia.com/compute/redist/jp/v60/pytorch/torch-2.4.0a0+07cecf4168.nv24.05.14710581-cp310-cp310-linux_aarch64.whl"
```
Don't use `pypi.jetson-ai-lab.io` for JetPack 6.0 — it served generic CUDA 13 builds that can't use the GPU.

### Build torchvision 0.19.0 from source
Install the build dependencies and check out the matching torchvision release:
```bash
sudo apt-get update
sudo apt-get install -y build-essential libjpeg-dev zlib1g-dev libpng-dev libpython3-dev \
    libopenblas-dev libavcodec-dev libavformat-dev libswscale-dev
cd ~
git clone --branch v0.19.0 https://github.com/pytorch/vision.git torchvision
```

The build takes hours, so run it inside **tmux** — a terminal session that keeps running on the Jetson even if your SSH connection drops:
```bash
tmux new -s torchvision-build
cd ~/torchvision
export BUILD_VERSION=0.19.0
export FORCE_CUDA=1    # build the CUDA versions of torchvision's ops (NMS etc.)
export MAX_JOBS=1      # one compile job at a time: slow, but won't run the Jetson out of memory
python3 setup.py build
```
Detach with `Ctrl-b` then `d`, and check on it later with `tmux attach -t torchvision-build`. **Don't run `setup.sh` or any other pip installs while it's building.**

Once the build finishes without errors, install it. `--user` puts it in `~/.local`, the same place as PyTorch:
```bash
cd ~/torchvision
python3 setup.py install --user
```

### Verify
Run this from **outside** the source directory — from inside `~/torchvision`, Python imports the local source folder instead of the installed package. The NMS call checks that torchvision's compiled CUDA code actually works, not just that it imports.
```bash
cd ~
python3 - <<'PY'
import torch
import torchvision

print("Torch:", torch.__version__)
print("Torchvision:", torchvision.__version__)
print("CUDA available:", torch.cuda.is_available())

boxes = torch.tensor(
    [[0, 0, 10, 10], [1, 1, 11, 11]],
    dtype=torch.float32,
    device="cuda"
)
scores = torch.tensor([0.9, 0.8], dtype=torch.float32, device="cuda")
print("CUDA NMS result:", torchvision.ops.nms(boxes, scores, 0.5))
PY
```
Expected:
```
Torch: 2.4.0a0+07cecf4168.nv24.05
Torchvision: 0.19.0
CUDA available: True
CUDA NMS result: tensor([0], device='cuda:0')
```

### Install Ultralytics without replacing PyTorch
Once the verify step passes:
```bash
python3 -m pip install --user --no-deps ultralytics==8.4.6
python3 -m pip check
```
8.4.6 is the version `yolo_ros` 4.7.1 asks for. `pip check` lists what Ultralytics still needs. `yolo_ros` itself also needs the packages in `~/auv_ws/src/yolo_ros/yolo_ros/requirements.txt` (e.g. `lap`) — install from that list by hand, never with `pip install -r`, because its `ultralytics` line would pull in a generic PyTorch. Install each missing package with `--no-deps`, skip torch and torchvision, and keep numpy below 2.

Then rerun the verify step above to confirm PyTorch is still NVIDIA's build, and launch the node:
```bash
cd ~/auv_ws
colcon build
source install/setup.bash
ros2 launch yolo_bringup yolo.launch.py
```
The first launch downloads the default model (`yolov8m.pt`), so the Jetson needs internet access (Step 4). By default it listens for images on `/camera/rgb/image_raw`; for now, just confirm the node starts without import errors.

### Don't break it
- **Never upgrade torch or torchvision with pip** (`pip install -U torch`, `pip install -U torchvision`). That replaces NVIDIA's build with generic wheels that can't use the GPU.
- **Never install Ultralytics without `--no-deps`**, and never `pip install -r` `yolo_ros`'s `requirements.txt`. Both pull in a generic PyTorch.
- **Keep numpy below 2.**
- **`setup.sh` is safe to rerun** once torchvision is installed: on a Jetson it skips `yolo_ros`'s `python3-torchvision-pip` and `python3-ultralytics-pip` rosdep keys. That only protects those two keys, though — any other pip package that depends on torch can still replace it, so check what a new package depends on before installing it.

---

## Troubleshooting quick reference

| Symptom | Likely cause | Where to look |
|---|---|---|
| Black screen or UEFI error booting a JetPack 6 SD card | Firmware bridge update (Step 2) was skipped | Step 2 |
| `apt update` fails with "Temporary failure resolving..." | No real internet route (direct static link) | Step 4 |
| `apt update` fails citing a repo "not valid yet" for a huge number of days | System clock is wrong | Step 4 |
| `Unable to locate package ros-humble-desktop` | ROS2 apt repo was never added | Step 5 |
| `colcon build` fails with `canonicalize_version() got an unexpected keyword argument` | A pip install upgraded setuptools to 80 or later | Rerun `setup.sh`, or `pip3 install "setuptools<80"` |
| `setup.sh` ends with "WARNING: yolo_ros won't run until this is fixed" | Step 7 isn't done yet (expected if you aren't working on vision), or a pip install replaced NVIDIA's PyTorch | Step 7 |
| `torch.cuda.is_available()` returns `False` | A generic PyTorch wheel replaced NVIDIA's (e.g. `pip install -U torch` or a plain `pip install ultralytics`) | Step 7 |
| `yolo_ros` builds but fails on launch with `No module named 'torch'`, `'torchvision'` or `'ultralytics'` | `colcon build` doesn't check Python imports, so missing packages only show up at launch | Step 7 |
| Verify step fails with `Could not run 'torchvision::nms' with arguments from the 'CUDA' backend` | torchvision was built without its CUDA ops | Delete `~/torchvision/build` and rebuild with `FORCE_CUDA=1` (Step 7) |
| SSH to a saved IP suddenly stops working | The IP changed (DHCP reassignment) or you're on the wrong subnet | Ping the address first from a plain terminal; check `ip addr` directly on the Jetson if unreachable |
| `ping` returns a reply from a totally different address than the one you pinged | Your computer has no route to that address on any interface and fell back to a default gateway | Check `ipconfig /all` (Windows) or `ip addr` (Linux) for the adapter actually connected to the Jetson |

---

## Where to go next

Once ROS2 and this repo are set up, `docs/architecture-roadmap.md` picks up from here — it covers how the sensors, control loop, and vision system fit together, and the order to build and test them in.
