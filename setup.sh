#!/bin/bash
set -e

if [ -z "$ROS_DISTRO" ]; then
  echo "ERROR: ROS_DISTRO is not set. Source ROS2 first:" >&2
  echo "  source /opt/ros/humble/setup.bash" >&2
  exit 1
fi

echo "Importing external driver repos..."
vcs import . < dependencies.repos

echo "Skipping zed-ros2-wrapper build by default (requires the real ZED SDK,"
echo "which is proprietary/GPU-dependent and can't be auto-installed here)."
echo "Once the SDK is installed, remove the ignore: rm zed-ros2-wrapper/COLCON_IGNORE"
touch zed-ros2-wrapper/COLCON_IGNORE

if ! command -v pip3 &> /dev/null; then
  echo "python3-pip not found -- installing..."
  sudo apt install -y python3-pip
fi


# Some rosdep-driven pip installs (e.g. yolo_ros's torch/torchvision) can pull
# in a setuptools version too new for colcon, breaking every build afterward
# with "canonicalize_version() got an unexpected keyword argument". Pin it
# proactively so this can't recur.
pip3 install "setuptools<80" --quiet

# On the Jetson, PyTorch has to be NVIDIA's CUDA build (docs/jetson-setup.md,
# Step 7). yolo_ros's rosdep keys pip-install generic torchvision/ultralytics,
# which would replace it with wheels that can't use the GPU, so skip them there.
IS_JETSON=false
ROSDEP_ARGS=()
if [ "$(uname -m)" = "aarch64" ] && [ -f /etc/nv_tegra_release ]; then
  IS_JETSON=true
  echo "Jetson detected -- skipping yolo_ros's pip torch keys to protect NVIDIA's PyTorch."
  ROSDEP_ARGS=(--skip-keys "python3-torchvision-pip python3-ultralytics-pip")
fi

echo "Installing ROS dependencies..."
cd ..
rosdep install --from-paths src --ignore-src -r -y "${ROSDEP_ARGS[@]}"

if ! python3 -c "import brping" 2>/dev/null; then
  echo "Installing bluerobotics-ping (Ping Sonar library)..."
  pip3 install bluerobotics-ping
fi

if ! python3 -c "import ms5837" 2>/dev/null; then
  echo "Installing ms5837 (Bar02 pressure sensor library)..."
  pip3 install git+https://github.com/bluerobotics/ms5837-python.git
fi

if ! command -v i2cdetect &> /dev/null; then
  echo "Installing i2c-tools..."
  sudo apt install -y i2c-tools
fi

# yolo_ros only runs once PyTorch, torchvision and Ultralytics work on the GPU.
# Warn instead of failing, since nothing else in the repo needs them.
if [ "$IS_JETSON" = true ]; then
  echo "Checking the vision node's Python dependencies..."
  python3 - <<'PY' || echo "WARNING: yolo_ros won't run until this is fixed. See docs/jetson-setup.md, Step 7."
import sys

try:
    import torch
except ImportError as exc:
    sys.exit(f"PyTorch can't be imported: {exc}")
if not torch.cuda.is_available():
    sys.exit(f"PyTorch {torch.__version__} can't use the GPU. A generic wheel may have replaced NVIDIA's.")

try:
    import torchvision
except ImportError as exc:
    sys.exit(f"PyTorch {torch.__version__} works, but torchvision can't be imported: {exc}")
try:
    boxes = torch.tensor([[0, 0, 10, 10], [1, 1, 11, 11]], dtype=torch.float32, device="cuda")
    scores = torch.tensor([0.9, 0.8], device="cuda")
    torchvision.ops.nms(boxes, scores, 0.5)
except Exception as exc:
    sys.exit(f"torchvision {torchvision.__version__} is installed, but its CUDA ops failed: {exc}")

try:
    import ultralytics
except ImportError as exc:
    sys.exit(f"PyTorch and torchvision work on the GPU, but Ultralytics can't be imported: {exc}")

print(f"PyTorch {torch.__version__}, torchvision {torchvision.__version__} and "
      f"Ultralytics {ultralytics.__version__} are ready.")
PY
fi

echo "Done. Now run: colcon build"
