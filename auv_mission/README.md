# auv_mission

Decides what the vehicle should currently be doing (search for a gate, center
on it, advance, move to the next task) and publishes that goal as a
`auv_msgs/Setpoint` for the controllers to act on.

## Status
Not yet implemented — package scaffold only.

## Planned nodes
- Mission planner node (state machine) — subscribes to `/odometry/filtered`
  and the target pose from `auv_vision`, publishes `auv_msgs/Setpoint`

## Planned topics
| Topic | Type | Direction |
|---|---|---|
| `/odometry/filtered` | `nav_msgs/Odometry` | Subscribe |
| Target pose (from `auv_vision`) | TBD | Subscribe |
| `/auv/setpoint` | `auv_msgs/Setpoint` | Publish |

## How to run
TBD — depends on `auv_localization` and `auv_vision` being functional first.
