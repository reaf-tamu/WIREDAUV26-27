# Issue: yolo_ros builds but can't run -- torch not installed

**Status:** Open, deferred -- not a current priority
**Last updated:** 2026-09-XX

## The problem

`colcon build` succeeds for `yolo_ros`, but the node can't actually run:

    ModuleNotFoundError: No module named 'torch'

Confirmed on the Jetson: `torch`/`torchvision`/`ultralytics` are not installed via pip or apt at all.

## Why this wasn't caught earlier

`colcon build` doesn't check whether a Python node's imports actually succeed -- only that the package structure is valid. This gap went unnoticed because nothing has tried to *launch* `yolo_ros` yet in this project.

## Why a plain pip install torch won't fix it

Generic PyPI PyTorch/CUDA wheels are x86_64-only and don't work on the Jetson's `aarch64` architecture. Real GPU-accelerated PyTorch on Jetson requires NVIDIA's own Jetson-specific wheel, matched to the exact JetPack/L4T version -- plus likely building `torchvision` from source to match. This is a real, somewhat involved task, not a one-line fix.

## Next steps, whenever this becomes a priority

1. Confirm exact JetPack/L4T version: `head -1 /etc/nv_tegra_release`
2. Find NVIDIA's matching PyTorch wheel for that version + Python 3.10
3. Build/install `torchvision` to match
4. Verify: `python3 -c "import torch; print(torch.__version__)"`
5. Only then attempt to actually launch `yolo_ros`

## References

- Related: `docs/setup.md`'s troubleshooting table (same underlying finding)
