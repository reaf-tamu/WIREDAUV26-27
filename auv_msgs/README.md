# auv_msgs

Custom ROS2 message definitions used across multiple packages. Standard messages
(sensor_msgs, nav_msgs, etc.) are used wherever they already fit — this package
only holds messages we needed to define ourselves.

## Messages

### Setpoint.msg
A single desired-state command, published by the mission planner (`auv_mission`)
and subscribed to by the controllers (`auv_control`).

| Field | Type | Meaning |
|---|---|---|
| `desired_pose` | `geometry_msgs/Pose` | Target position + orientation |
| `desired_velocity` | `geometry_msgs/Twist` | Target velocity, used only if `use_velocity_control` is true |
| `use_velocity_control` | `bool` | Whether the controllers should hold a velocity instead of a pose |

## Why this exists instead of a standard message
No standard ROS2 message combines a target pose, a target velocity, and a mode flag
in one place, which is what the controllers need to receive as a single atomic update.
