# Handoff: get torchvision working on the Jetson

**Date:** 2026-10-15
**Status:** torch is installed and GPU-verified. torchvision is not installed and has not been built yet.
**Supersedes:** `docs/issues/yolo-torch-not-installed.md` (stale, it says torch is missing)

## Goal

`import torch` and `import torchvision` both work on the Jetson with CUDA enabled, so `yolo_ros` can run.

## Why this is needed

- `yolo_ros` is the ROS2 wrapper around Ultralytics YOLO. It needs torch and torchvision to run.
- `colcon build` succeeds without them, so the failure only shows up when the node launches.
- The Jetson is aarch64 with a fixed CUDA (12.2). A normal `pip install torch torchvision` pulls generic CUDA 13 wheels that don't work here (`torch.cuda.is_available()` returns False).
- NVIDIA ships a Jetson-specific torch wheel (installed). It does **not** ship a matching torchvision wheel, so torchvision has to be built from source against that exact torch.

## Currently installed (Jetson)

| Item | Version | How to check |
|---|---|---|
| OS | Ubuntu 22.04.4 LTS | `lsb_release -a` |
| Python | 3.10.12 | `python3 --version` |
| Architecture | aarch64 | `uname -m` |
| JetPack / L4T | 6.0 / 36.3 | stated by team; verify with `head -1 /etc/nv_tegra_release` |
| CUDA | 12.2 | JetPack 6.0 release notes |
| ROS2 | Humble | project setup |
| torch | 2.4.0a0+07cecf4168.nv24.05 | import works, `torch.cuda.is_available()` is True |
| torchvision | **not installed** (target v0.19.0) | |
| pip | 22.0.2 | `pip3 --version` |
| colcon_core | 0.21.0 (needs setuptools<80) | |
| numpy / pillow (system) | 1.21.5 / 9.0.1 | |

torch wheel used:
`https://developer.download.nvidia.com/compute/redist/jp/v60/pytorch/torch-2.4.0a0+07cecf4168.nv24.05.14710581-cp310-cp310-linux_aarch64.whl`

Target torchvision is v0.19.0. An NVIDIA forum post describes compiling 0.19.0 for this exact torch build: [Compiling torchvision 0.19.0 for torch 2.4.0a0+07cecf4168.nv24.05.14710581](https://forums.developer.nvidia.com/t/compiling-torchvision-0-19-0-for-torch-2-4-0a0-07cecf4168-nv24-05-14710581/306300). We have not attempted it.

## Check current state first

```bash
pip3 show torchvision
pip3 list | grep -i -E "nvidia|cuda|triton|numpy|setuptools"
```

- Failed installs earlier may have left `nvidia-*-cu13`, `cuda-toolkit`, `triton` and `setuptools 84.0.0` in `~/.local`. Only torch/torchvision were uninstalled; this has not been checked.
- setuptools 84 breaks `colcon build`. If present: `pip3 install "setuptools<80"`.
- Keep numpy < 2. torch 2.4 was built for numpy 1.x.
- Decide whether to remove the leftover cu13 packages (unconfirmed whether they interfere).

## Steps

From NVIDIA forum and Jetson guides. **Not yet run on our board.**

```bash
sudo apt-get install libjpeg-dev zlib1g-dev libpython3-dev libopenblas-dev \
    libavcodec-dev libavformat-dev libswscale-dev
git clone --branch v0.19.0 https://github.com/pytorch/vision torchvision
cd torchvision
export BUILD_VERSION=0.19.0
python3 setup.py install --user
cd ../
```

It is a long C++ build. `--user` matches where torch was installed (`~/.local`).

## Verify

The NMS call proves the compiled CUDA ops work, not just the import.

```bash
python3 -c "
import torch, torchvision
print(torch.__version__, torchvision.__version__, torch.cuda.is_available())
b = torch.tensor([[0,0,10,10],[1,1,11,11]], dtype=torch.float32).cuda()
s = torch.tensor([0.9, 0.8]).cuda()
print(torchvision.ops.nms(b, s, 0.5))
"
```

Expected: torch `2.4.0a0+07cecf4168.nv24.05`, torchvision `0.19.0...`, `True`, and a tensor.

## Don't break it

- Never `pip install -U torch/torchvision` or plain `pip install ultralytics`. Use `pip3 install ultralytics --no-deps`.
- Don't re-run `./setup.sh` or `rosdep` on the whole workspace yet. `yolo_ros`'s rosdep step ran `pip3 install -U torchvision/ultralytics` earlier. Find the keys in `yolo_ros`'s `package.xml` and use `rosdep --skip-keys` (key names not checked).
- Don't use `pypi.jetson-ai-lab.io` for JetPack 6.0. It served generic cu130 builds.
- Docker `l4t-pytorch` is not a fit, since `yolo_ros` runs on the host.

## After torchvision works

1. `pip3 install ultralytics --no-deps`, install what it still needs, re-run the verify step (untested).
2. Launch `yolo_ros` and confirm it starts (check its real launch file name).
3. Fold the working steps into `docs/setup.md` and `setup.sh`, with a guard so rosdep can't overwrite torch.

## Context

- Related: `docs/setup.md` (troubleshooting table), `docs/issues/usb-hub-power.md` (issue doc format).
- Vision isn't blocking other work right now.
