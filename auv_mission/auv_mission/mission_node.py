#!/usr/bin/env python3
"""
mission_node.py -- runs the December gate try (gate_run.py) on the robot.

How the run starts (whichever happens first):
  - something publishes True on /auv/mission_start (the mission switch node
    will do this once it exists, task E3), or
  - start_delay_s seconds pass after the node starts (set it to -1.0 to turn
    the timer off and only use the switch).

Subscribes:
  /odometry/filtered   (nav_msgs/Odometry)  current depth (z) and heading
  /auv/mission_start   (std_msgs/Bool)      True = go
Publishes:
  /auv/setpoint        (auv_msgs/Setpoint)  what the controllers should hold
  /auv/mission_state   (std_msgs/String)    current state, for logs and rosbags

Depth: the pressure node and the EKF use z = -depth (underwater is negative),
so this node sends desired_pose.position.z = -depth. If the robot goes UP
when it should go down at the pool, the sign is wrong somewhere in the
vertical chain (task K3), not here.

Forward speed: until the DVL is in the EKF (task S7), the robot doesn't know
its forward speed. Set surge_ki and surge_kd to 0 in pid_gains.yaml for this
run, so surge_cmd acts like a fixed throttle (output = surge_kp * surge_cmd).
"""

import math

import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from std_msgs.msg import Bool, String
from auv_msgs.msg import Setpoint

from auv_mission.gate_run import GateRun, GateRunParams


def quaternion_to_yaw(q):
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


def yaw_to_quaternion(yaw):
    """Level (roll = pitch = 0) orientation with the given heading."""
    return 0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0)


class MissionNode(Node):
    def __init__(self):
        super().__init__('mission_node')

        defaults = GateRunParams()
        for name, value in vars(defaults).items():
            self.declare_parameter(name, value)
        self.declare_parameter('start_delay_s', 10.0)
        self.declare_parameter('rate_hz', 10.0)

        params = GateRunParams(**{name: float(self.get_parameter(name).value)
                                  for name in vars(defaults)})
        self.mission = GateRun(params)
        self.start_delay_s = float(self.get_parameter('start_delay_s').value)

        self.depth_m = 0.0
        self.yaw = 0.0
        self.have_odom = False
        self.start_requested = False
        self.last_state = None
        self.t0 = self._now()

        self.create_subscription(Odometry, '/odometry/filtered', self.odom_callback, 10)
        self.create_subscription(Bool, '/auv/mission_start', self.start_callback, 10)
        self.setpoint_pub = self.create_publisher(Setpoint, '/auv/setpoint', 10)
        self.state_pub = self.create_publisher(String, '/auv/mission_state', 10)

        rate = float(self.get_parameter('rate_hz').value)
        self.timer = self.create_timer(1.0 / rate, self.tick)
        if self.start_delay_s >= 0:
            self.get_logger().info(f'Mission starts in {self.start_delay_s:.0f} s '
                                   '(or on /auv/mission_start)')
        else:
            self.get_logger().info('Waiting for /auv/mission_start')

    def _now(self):
        return self.get_clock().now().nanoseconds / 1e9

    def odom_callback(self, msg: Odometry):
        self.depth_m = -msg.pose.pose.position.z   # z = -depth (see docstring)
        self.yaw = quaternion_to_yaw(msg.pose.pose.orientation)
        self.have_odom = True
        self.mission.sensor_update(self._now())

    def start_callback(self, msg: Bool):
        if msg.data:
            self.start_requested = True

    def tick(self):
        t = self._now()
        if self.start_delay_s >= 0 and t - self.t0 >= self.start_delay_s:
            self.start_requested = True
        # Never start without at least one odometry message: we need the heading.
        start = self.start_requested and self.have_odom

        cmd = self.mission.step(t, self.depth_m, self.yaw, start=start)

        sp = Setpoint()
        sp.desired_pose.position.z = -cmd.depth_m
        o = sp.desired_pose.orientation
        o.x, o.y, o.z, o.w = yaw_to_quaternion(cmd.yaw_rad)
        sp.desired_velocity.linear.x = cmd.surge
        sp.use_velocity_control = False
        sp.use_altitude_hold = False
        self.setpoint_pub.publish(sp)

        if cmd.state != self.last_state:
            why = f' ({self.mission.reason})' if cmd.state == 'ABORT' else ''
            self.get_logger().info(f'{t - self.t0:6.1f} s  -> {cmd.state}{why}')
            self.last_state = cmd.state
        state_msg = String()
        state_msg.data = cmd.state
        self.state_pub.publish(state_msg)


def main(args=None):
    rclpy.init(args=args)
    node = MissionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
