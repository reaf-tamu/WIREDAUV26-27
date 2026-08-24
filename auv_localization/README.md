# auv_localization

Combines data from multiple sensors into one continuous estimate of the vehicle's
position, orientation, and velocity, using an Extended Kalman Filter (EKF) via the
`robot_localization` package.

## Status
Not yet implemented — package scaffold only. Waiting on sensor hardware to configure
and test the actual EKF fusion.

## Planned nodes
- EKF node (from `robot_localization`, configured via `config/ekf.yaml`)

## Planned topics
| Topic | Type | Direction | Notes |
|---|---|---|---|
| `/vectornav/imu` | `sensor_msgs/Imu` | Subscribe | Orientation + angular velocity input |
| `/depth` | (TBD) | Subscribe | From pressure sensor, once wired |
| `/dvl/twist` | (TBD) | Subscribe | From DVL, once wired |
| `/odometry/filtered` | `nav_msgs/Odometry` | Publish | Combined state estimate, used by `auv_control` and `auv_mission` |

## Config
- `config/ekf.yaml` — tells the EKF which fields to trust from which sensor. Not yet written.

## How to run
TBD once sensors are wired and the EKF config exists.
