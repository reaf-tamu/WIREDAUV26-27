"""
attitude_control_node.py

Runs the PID loops for all four attitude/depth axes. Sensor feedback and
gains are wired up for all of them, but actuation readiness differs:

  - yaw hold: REAL sensor feedback (VN-100 -> EKF), AND the allocator has
    real (if still bench-unverified) yaw mixing -- see
    thruster_allocator_node.py. Gains default to 0 (does nothing) until
    that sign is bench-confirmed AND real tuning happens.

  - depth hold: real state placeholder only -- no pressure sensor wired
    in yet, so /odometry/filtered's z means nothing right now. Heave
    actuation DOES exist in the allocator (vertical thrusters move as one
    group), so once a real depth sensor exists, enabling this is a
    tuning exercise, not a rewrite.

  - roll hold / pitch hold: REAL sensor feedback (VN-100 -> EKF gives a
    genuine roll/pitch estimate right now) -- but the allocator does NOT
    yet mix torque.x/torque.y into anything. The 4 vertical thrusters'
    corner positions aren't confirmed, so there's no known-good way to
    drive them independently for roll/pitch. These PIDs are wired up and
    will publish real torque.x/torque.y values once tuned, but the
    allocator currently reads and silently ignores those fields -- so
    tuning these before the allocator supports them has NO physical
    effect yet. Do the allocator work first; this is just here so no
    rewrite is needed once that's done.

Sway is not implemented -- not physically possible with this thruster
layout (differential drive, no lateral thrust capability).

Subscribes:
  /odometry/filtered  (nav_msgs/Odometry)
  /auv/setpoint        (auv_msgs/Setpoint)
Publishes:
  /auv/wrench          (geometry_msgs/Wrench)
"""

import math

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Wrench
from nav_msgs.msg import Odometry
from auv_msgs.msg import Setpoint

from auv_control.pid import PID


# data actual and ideal states are published to topic in quaternions, convert to meaningful yaw value
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
    sinp = max(-1.0, min(1.0, sinp))  # clamp -- guards against tiny float
    # errors pushing this a hair outside asin()'s valid [-1, 1] domain
    return math.asin(sinp)


# make sure robot takes shortest correction path (1deg vs 359deg)
def shortest_angle_diff(target, current):
    """Angle difference wrapped to [-pi, pi] -- without this, +179 deg and
    -179 deg would compute as a ~358 degree error instead of the real ~2."""
    diff = target - current
    while diff > math.pi:
        diff -= 2.0 * math.pi
    while diff < -math.pi:
        diff += 2.0 * math.pi
    return diff


class AttitudeControlNode(Node):
    def __init__(self):
        super().__init__('attitude_control_node')

        # declare and get parameters from yaml file
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

        self.current_roll = 0.0
        self.current_pitch = 0.0
        self.current_yaw = 0.0
        self.current_depth = 0.0
        self.setpoint_roll = 0.0
        self.setpoint_pitch = 0.0
        self.setpoint_yaw = 0.0
        self.setpoint_depth = 0.0
        self.surge_command = 0.0

        self.last_time = self.get_clock().now()

        self.create_subscription(Odometry, '/odometry/filtered', self.odom_callback, 10)
        self.create_subscription(Setpoint, '/auv/setpoint', self.setpoint_callback, 10)
        self.wrench_pub = self.create_publisher(Wrench, '/auv/wrench', 10)

        # Fixed-rate timer rather than reacting only to new odometry --
        # keeps dt well-defined even if a sensor briefly drops a message.
        self.timer = self.create_timer(0.05, self.control_loop)  # 20 Hz

    # reads msg Odometry msg from topic (actual state according to sensors)
    def odom_callback(self, msg: Odometry):
        self.current_roll = quaternion_to_roll(msg.pose.pose.orientation)
        self.current_pitch = quaternion_to_pitch(msg.pose.pose.orientation)
        self.current_yaw = quaternion_to_yaw(msg.pose.pose.orientation)
        self.current_depth = msg.pose.pose.position.z

    # reads Setpoint msg from topic (desired state according to mission logic)
    def setpoint_callback(self, msg: Setpoint):
        self.setpoint_roll = quaternion_to_roll(msg.desired_pose.orientation)
        self.setpoint_pitch = quaternion_to_pitch(msg.desired_pose.orientation)
        self.setpoint_yaw = quaternion_to_yaw(msg.desired_pose.orientation)
        self.setpoint_depth = msg.desired_pose.position.z
        self.surge_command = msg.desired_velocity.linear.x

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

        depth_output = self.depth_pid.update(
            setpoint=self.setpoint_depth, measurement=self.current_depth, dt=dt)

        wrench = Wrench()
        wrench.force.x = self.surge_command   # open-loop, see class docstring
        wrench.force.y = 0.0                  # sway not achievable
        wrench.force.z = depth_output
        # NOTE: torque.x/torque.y are real PID output now, but the
        # allocator doesn't mix them into anything yet -- see class
        # docstring. Publishing nonzero values here currently has NO
        # physical effect until that's added.
        wrench.torque.x = roll_output
        wrench.torque.y = pitch_output
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
