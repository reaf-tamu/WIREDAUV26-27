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

echo "Installing ROS dependencies..."
cd ..
rosdep install --from-paths src --ignore-src -r -y

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

echo "Done. Now run: colcon build"
