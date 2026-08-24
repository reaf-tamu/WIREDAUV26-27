# Zed Mini — How To

**Owner(s):** [assign]
**Last updated:** 2026-08-24 by (pre-filled scaffold, not yet verified with real hardware)
**Status:** Not yet wired — sections below are pre-filled from documentation only, not hands-on testing

---

## 1. Overview
A stereo camera: two lenses provide RGB images plus a computed depth map, used for
recognizing competition objects (gates, buoys, markers).

| | |
|---|---|
| Manufacturer / model | Stereolabs Zed Mini |
| Interface | USB |
| Datasheet | [add link] |
| Product page | [add link] |
| Driver repo | https://github.com/stereolabs/zed-ros2-wrapper |
| Approx. cost | [add] |

## 2. What it does and why we use it
- **Sensing principle:** compares the left and right lens images to triangulate distance (stereo vision).
- **Raw output:** left/right RGB images, depth map / point cloud.
- **ROS2 message type:** image topics (`sensor_msgs/Image`), depth topics.
- **Where it goes:** RGB feed goes to the YOLO detection node (`yolo_ros`); depth feed goes to `auv_vision` for combining with detections into 3D target positions.
- **What breaks without it:** no object detection input — mission planner has no way to identify gates/buoys/markers.

## 3. Hardware setup
### Mounting
[TODO once hardware is in hand — forward-facing, mounting position/angle matters for FOV coverage.]
### Wiring
| Sensor pin | Connects to | Notes |
|---|---|---|
| USB | Jetson USB port | |
### Safety notes
[TODO — waterproof housing considerations]

## 4. Software setup
### Prerequisites
Requires the ZED SDK installed (matched to JetPack/CUDA version — see `docs/jetson-setup.md` for our JetPack version) before the ROS2 wrapper will build.
### Where the code lives
External package, cloned via `dependencies.repos`.
### Install / build
```bash
cd ~/auv_ws/src
git clone https://github.com/stereolabs/zed-ros2-wrapper.git
cd ~/auv_ws && rosdep install --from-paths src --ignore-src -r -y
colcon build --packages-select zed_wrapper zed_components --symlink-install
```

## 5. Running it
```bash
ros2 launch zed_wrapper zed_camera.launch.py camera_model:=zedm
```
### Verify it's working
```bash
ros2 topic echo /zed/zed_node/rgb/image_rect_color --no-arr
ros2 topic echo /zed/zed_node/depth/depth_registered --no-arr
```

## 6. Calibration
- **Does this sensor need calibration?** Factory-calibrated stereo pair; no user calibration needed for basic use. [Confirm once hardware is in hand.]

## 9. Troubleshooting
| Symptom | Likely cause | Fix |
|---|---|---|
| Build fails referencing CUDA | ZED SDK not installed, or version mismatch with JetPack | Reinstall the ZED SDK version matching our JetPack version |

## 13. References
- Driver repo: https://github.com/stereolabs/zed-ros2-wrapper
