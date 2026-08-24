# auv_control

PID control loops that stabilize the vehicle (roll, pitch, yaw, depth, and
eventually surge/sway), and thruster allocation that converts the combined
correction into individual thruster commands.

## Status
Not yet implemented — package scaffold only.

## Planned nodes
- PID controller node — subscribes to `/odometry/filtered` (feedback) and
  `/auv/setpoint` (`auv_msgs/Setpoint`, desired state), publishes a
  `geometry_msgs/Wrench`
- Thruster allocation node — subscribes to the wrench, publishes individual
  thruster commands

## Planned topics
| Topic | Type | Direction |
|---|---|---|
| `/odometry/filtered` | `nav_msgs/Odometry` | Subscribe |
| `/auv/setpoint` | `auv_msgs/Setpoint` | Subscribe |
| `/auv/wrench` | `geometry_msgs/Wrench` | Publish (from PID node) / Subscribe (thruster allocation node) |
| Individual thruster commands | TBD | Publish |

## Config
PID gains will live in a YAML config file per loop, not hardcoded — see the
Parameters section of `docs/architecture-roadmap.md`. Not yet written.

## Tuning log
Will be tracked here once the vehicle is testable — see
`docs/sensors/_template.md` for the format we use elsewhere for tuning history.

## How to run
TBD, and should be bench-tested (vehicle in a stand, not in water) before any
in-water test — see `docs/architecture-roadmap.md` Stage 3.
