# auv_vision

Takes YOLO detections (from the external `yolo_ros` package) and the Zed mini's
depth image, and combines them into a 3D target position in the vehicle's own
coordinate frame, for the mission planner to use.

## Status
Not yet implemented — package scaffold only.

## Depends on (external packages, not part of this repo)
- `zed-ros2-wrapper` — camera driver, provides RGB + depth
- `yolo_ros` — runs YOLO inference on the RGB stream

## Planned nodes
- Target pose node — subscribes to YOLO detections + depth image, publishes a
  target position in `base_link` frame using a static `tf2` transform
  (camera → `base_link`)

## Planned topics
| Topic | Type | Direction |
|---|---|---|
| `/yolo/detections` | (from `yolo_ros`) | Subscribe |
| `/zed/zed_node/depth/depth_registered` | (from `zed-ros2-wrapper`) | Subscribe |
| Target pose | TBD | Publish, consumed by `auv_mission` |

## How to run
TBD once the Zed mini is wired and `yolo_ros` is trained on our objects
(gates, buoys, markers).
