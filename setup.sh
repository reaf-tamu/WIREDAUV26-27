#!/bin/bash
# auv_software/setup.sh — run once after cloning, and again whenever
# dependencies.repos changes.
set -e
echo "Importing external driver repos..."
vcs import . < dependencies.repos

echo "Installing ROS dependencies..."
cd ../..   # up to workspace root, adjust if your layout differs
rosdep install --from-paths src --ignore-src -r -y

echo "Done. Now run: colcon build"
