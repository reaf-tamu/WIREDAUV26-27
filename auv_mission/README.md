# auv_mission

Decides what the vehicle should be doing right now and publishes it as an
`auv_msgs/Setpoint` for the controllers in `auv_control` to hold.

## Status
**v0: the December pre-qual try.** A timed run with no vision:

| Step | What the robot does | Moves on when |
|---|---|---|
| WAIT | Stays at the surface, remembers which way it's pointed | Mission switch, or `start_delay_s` after launch |
| DIVE | Goes to `target_depth_m`, holds that heading | Within `depth_tolerance_m` of the depth for `depth_settle_s` |
| DRIVE | Holds depth + heading, pushes forward with `surge_cmd` | `drive_time_s` has passed |
| SURFACE | Stops pushing forward, comes up | `surface_time_s` has passed |
| DONE | Stays at the surface | Never |
| ABORT | Same as SURFACE. Happens if DIVE takes longer than `dive_timeout_s`, the whole run takes longer than `mission_timeout_s`, or odometry stops for `sensor_timeout_s` | Never |

The logic lives in `auv_mission/gate_run.py` with no ROS in it, so you can
test it on a laptop. `auv_mission/mission_node.py` wraps it in a ROS 2 node.

Next versions add vision (search for the gate, line up, then go through,
from PDR slide 103) once `auv_vision` publishes a target position.

## Topics
| Topic | Type | Direction |
|---|---|---|
| `/odometry/filtered` | `nav_msgs/Odometry` | Subscribe (depth from z, heading from orientation) |
| `/auv/mission_start` | `std_msgs/Bool` | Subscribe (True = go; the mission switch node will publish this) |
| `/auv/setpoint` | `auv_msgs/Setpoint` | Publish |
| `/auv/mission_state` | `std_msgs/String` | Publish (current step, for rosbags) |

## How to run
```bash
colcon build --packages-select auv_mission
source install/setup.bash
ros2 launch auv_mission mission.launch.py     # settings in config/december_gate.yaml
```
Run it alongside `auv_control` (control.launch.py) and `auv_localization`.

## Before the pool
- **Depth sign.** This node sends `position.z = -depth`, matching the pressure
  node and the EKF (underwater = negative z). Check on the bench that a deeper
  setpoint makes the vertical thrusters push down.
- **Pressure in the EKF.** Depth hold needs the pressure sensor (pose0) turned on
  in `auv_localization/config/ekf.yaml`.
- **Forward speed.** Without the DVL in the EKF the robot doesn't know its speed.
  Set `surge_ki: 0.0` and `surge_kd: 0.0` in `pid_gains.yaml`, so `surge_cmd`
  works as a fixed throttle (output = `surge_kp` × `surge_cmd`).
- **Gains.** `pid_gains.yaml` is still all zeros. The sim used yaw kp 0.8 / kd 0.2,
  depth kp 3.0 / ki 0.5 / kd 1.0, surge kp 4.0. Start there and tune in the water.
- **Drive time.** Start about 3 m behind the gate. 25 s at full throttle went
  about 5 m in the sim. Time it at the pool and change `drive_time_s`.
- **Kill switch in hand** for every run.

## Tests
```bash
python3 -m pytest auv_mission/test      # no ROS needed
```
The Python sim (`wired-controls-sim`) has `mission_sim.py`, which runs this node
with the real control code against the robot model.
