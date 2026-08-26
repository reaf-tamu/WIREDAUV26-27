#!/bin/bash
set -e

echo "Importing external driver repos..."
vcs import . < dependencies.repos

echo "Installing ROS dependencies..."
cd ..
rosdep install --from-paths src --ignore-src -r -y

# ping_sonar_ros bundles the brping driver as a submodule whose __init__.py
# does an absolute self-import (`from brping.definitions import *`), which only
# resolves if the parent ping-python/ folder is itself on PYTHONPATH.
PING_PYTHON_PATH="$(pwd)/install/ping_sonar_ros/lib/python3.10/site-packages/ping_sonar_ros/ping-python"
if ! grep -qF "$PING_PYTHON_PATH" ~/.bashrc 2>/dev/null; then
  echo "export PYTHONPATH=\$PYTHONPATH:$PING_PYTHON_PATH" >> ~/.bashrc
  echo "Added ping-python to PYTHONPATH in ~/.bashrc (source ~/.bashrc or open a new terminal to pick it up)"
fi

echo "Done. Now run: colcon build"
