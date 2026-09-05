"""
attitude_control_node.py

Runs the PID loops for all attitude/depth/altitude/surge axes. Sensor
feedback and gains are wired up for all of them, but actuation/sensor
readiness differs:

  - yaw hold: REAL sensor feedback (VN-100 -> EKF), AND the allocator has
    real (if still bench-unverified) yaw mixing -- see
    thruster_allocator_node.py.

  - surge hold: closed-loop structure is real, but current_surge_velocity
    comes from /odometry/filtered's twist.linear.x, which is only
    meaningful once the DVL is fused into the EKF (odom0 in
    auv_localization/config/ekf.yaml).

  - depth hold: real state placeholder only -- no pressure sensor wired
    in yet, so /odometry/filtered's z means nothing right now.

  - altitude hold: SEPARATE from depth -- reads directly from the Ping
    Sonar's range topic, NOT from the EKF (altitude is never fused into
    the EKF's position estimate; see docs discussion). Only one of
    depth_pid / altitude_pid drives the vertical thrusters at a time,
    chosen by Setpoint.use_altitude_hold, since running both at once would
    mean two controllers fighting over the same thrusters.
    TODO: verify the actual Ping Sonar range topic name/type once that
    driver is running -- placeholder below is a guess (sensor_msgs/Range
    is the standard ROS2 type for a single-beam rangefinder, but the exact
    topic name needs confirming with `ros2 topic list` against the real
    ping_sonar_ros driver).

  - roll hold / pitch hold: real sensor feedback exists, but the allocator
    doesn't mix torque.x/torque.y into anything yet (vertical thruster
    corner positions unconfirmed) -- publishing these currently has no
    physical effect.

Sway is not implemented -- not physically possible with this thruster
layout.

Subscribes:
  /odometry/filtered  (nav_msgs/Odometry)
  /auv/setpoint        (auv_msgs/Setpoint)
  /ping1d/range        (sensor_msgs/Range) -- TODO: confirm real topic name
Publishes:
  /auv/wrench          (geometry_msgs/Wrench)
"""

import math

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Wrench
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Range
from auv_msgs.msg import Setpoint

from auv_control.pid import PID


def quaternion_to_yaw(q):
    """Extract yaw (rotation about Z) from a quaternion, in radians."""
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


def quaternion_to_roll(q):
    """Extract roll (rotation about X) from a quaternion, in radians."""
    sinr_cosp = 2.0 * (q.w * q.x + q.y * q.z)
    cosr_cosp = 1.0 - 2.0 * (q.x * q.x + q.y * q.y)
    return math.atan2(sinr_cosp, cosr_cosp)


def quaternion_to_pitch(q):
    """Extract pitch (rotation about Y) from a quaternion, in radians."""
    sinp = 2.0 * (q.w * q.y - q.z * q.x)
    sinp = max(-1.0, min(1.0, sinp))
    return math.asin(sinp)


def shortest_angle_diff(target, current):
    """Angle difference wrapped to [-pi, pi]."""
    diff = target - current
    while diff > math.pi:
        diff -= 2.0 * math.pi
    while diff < -math.pi:
        diff += 2.0 * math.pi
    return diff


class AttitudeControlNode(Node):
    def __init__(self):
        super().__init__('attitude_control_node')

        self.declare_parameter('roll_kp', 0.0)
        self.declare_parameter('roll_ki', 0.0)
        self.declare_parameter('roll_kd', 0.0)
        self.declare_parameter('pitch_kp', 0.0)
        self.declare_parameter('pitch_ki', 0.0)
        self.declare_parameter('pitch_kd', 0.0)
        self.declare_parameter('yaw_kp', 0.0)
        self.declare_parameter('yaw_ki', 0.0)
        self.declare_parameter('yaw_kd', 0.0)
        self.declare_parameter('depth_kp', 0.0)
        self.declare_parameter('depth_ki', 0.0)
        self.declare_parameter('depth_kd', 0.0)
        self.declare_parameter('altitude_kp', 0.0)
        self.declare_parameter('altitude_ki', 0.0)
        self.declare_parameter('altitude_kd', 0.0)
        self.declare_parameter('surge_kp', 0.0)
        self.declare_parameter('surge_ki', 0.0)
        self.declare_parameter('surge_kd', 0.0)

        self.roll_pid = PID(
            kp=self.get_parameter('roll_kp').value,
            ki=self.get_parameter('roll_ki').value,
            kd=self.get_parameter('roll_kd').value,
            output_limits=(-1.0, 1.0)
        )
        self.pitch_pid = PID(
            kp=self.get_parameter('pitch_kp').value,
            ki=self.get_parameter('pitch_ki').value,
            kd=self.get_parameter('pitch_kd').value,
            output_limits=(-1.0, 1.0)
        )
        self.yaw_pid = PID(
            kp=self.get_parameter('yaw_kp').value,
            ki=self.get_parameter('yaw_ki').value,
            kd=self.get_parameter('yaw_kd').value,
            output_limits=(-1.0, 1.0)
        )
        self.depth_pid = PID(
            kp=self.get_parameter('depth_kp').value,
            ki=self.get_parameter('depth_ki').value,
            kd=self.get_parameter('depth_kd').value,
            output_limits=(-1.0, 1.0)
        )
        self.altitude_pid = PID(
            kp=self.get_parameter('altitude_kp').value,
            ki=self.get_parameter('altitude_ki').value,
            kd=self.get_parameter('altitude_kd').value,
            output_limits=(-1.0, 1.0)
        )
        self.surge_pid = PID(
            kp=self.get_parameter('surge_kp').value,
            ki=self.get_parameter('surge_ki').value,
            kd=self.get_parameter('surge_kd').value,
            output_limits=(-1.0, 1.0)
        )

        self.current_roll = 0.0
        self.current_pitch = 0.0
        self.current_yaw = 0.0
        self.current_depth = 0.0
        self.current_altitude = 0.0  # from sonar directly, NOT the EKF
        self.current_surge_velocity = 0.0  # from EKF twist -- meaningless until DVL is fused in

        self.setpoint_roll = 0.0
        self.setpoint_pitch = 0.0
        self.setpoint_yaw = 0.0
        self.setpoint_depth = 0.0
        self.setpoint_altitude = 0.0
        self.setpoint_surge_velocity = 0.0
        self.use_altitude_hold = False  # picks depth_pid vs altitude_pid for the vertical axis

        self.last_time = self.get_clock().now()

        self.create_subscription(Odometry, '/odometry/filtered', self.odom_callback, 10)
        self.create_subscription(Setpoint, '/auv/setpoint', self.setpoint_callback, 10)
        # TODO: confirm this is the real ping_sonar_ros topic name once that
        # driver is actually running -- check with `ros2 topic list`.
        self.create_subscription(Range, '/ping1d/range', self.range_callback, 10)
        self.wrench_pub = self.create_publisher(Wrench, '/auv/wrench', 10)

        self.timer = self.create_timer(0.05, self.control_loop)  # 20 Hz

    def odom_callback(self, msg: Odometry):
        self.current_roll = quaternion_to_roll(msg.pose.pose.orientation)
        self.current_pitch = quaternion_to_pitch(msg.pose.pose.orientation)
        self.current_yaw = quaternion_to_yaw(msg.pose.pose.orientation)
        self.current_depth = msg.pose.pose.position.z
        self.current_surge_velocity = msg.twist.twist.linear.x

    def range_callback(self, msg: Range):
        # Altitude comes straight from the sonar -- deliberately never
        # touches the EKF. See module docstring for why.
        self.current_altitude = msg.range

    def setpoint_callback(self, msg: Setpoint):
        self.setpoint_roll = quaternion_to_roll(msg.desired_pose.orientation)
        self.setpoint_pitch = quaternion_to_pitch(msg.desired_pose.orientation)
        self.setpoint_yaw = quaternion_to_yaw(msg.desired_pose.orientation)
        self.setpoint_depth = msg.desired_pose.position.z
        self.setpoint_surge_velocity = msg.desired_velocity.linear.x
        self.use_altitude_hold = msg.use_altitude_hold
        # When in altitude mode, the setpoint's z field is repurposed to
        # mean "desired altitude" rather than "desired depth" -- avoids
        # needing a second position field in the message.
        if self.use_altitude_hold:
            self.setpoint_altitude = msg.desired_pose.position.z

    def control_loop(self):
        now = self.get_clock().now()
        dt = (now - self.last_time).nanoseconds / 1e9
        self.last_time = now
        if dt <= 0.0:
            return

        roll_error = shortest_angle_diff(self.setpoint_roll, self.current_roll)
        roll_output = self.roll_pid.update(setpoint=0.0, measurement=-roll_error, dt=dt)

        pitch_error = shortest_angle_diff(self.setpoint_pitch, self.current_pitch)
        pitch_output = self.pitch_pid.update(setpoint=0.0, measurement=-pitch_error, dt=dt)

        yaw_error = shortest_angle_diff(self.setpoint_yaw, self.current_yaw)
        yaw_output = self.yaw_pid.update(setpoint=0.0, measurement=-yaw_error, dt=dt)

        surge_output = self.surge_pid.update(
            setpoint=self.setpoint_surge_velocity,
            measurement=self.current_surge_velocity, dt=dt)

        # Only one of these ever drives the thrusters -- see module
        # docstring for why running both at once would be unsafe.
        if self.use_altitude_hold:
            vertical_output = self.altitude_pid.update(
                setpoint=self.setpoint_altitude,
                measurement=self.current_altitude, dt=dt)
            # Reset the one NOT currently active, so its integral term
            # doesn't sit accumulating stale error while unused -- avoids
            # a sudden kick if control ever switches back mid-mission.
            self.depth_pid.reset()
        else:
            vertical_output = self.depth_pid.update(
                setpoint=self.setpoint_depth,
                measurement=self.current_depth, dt=dt)
            self.altitude_pid.reset()

        wrench = Wrench()
        wrench.force.x = surge_output
        wrench.force.y = 0.0                  # sway not achievable
        wrench.force.z = vertical_output
        wrench.torque.x = roll_output         # allocator doesn't use this yet
        wrench.torque.y = pitch_output        # allocator doesn't use this yet
        wrench.torque.z = yaw_output

        self.wrench_pub.publish(wrench)


def main(args=None):
    rclpy.init(args=args)
    node = AttitudeControlNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
