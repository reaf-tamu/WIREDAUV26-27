"""
attitude_control_node.py

Runs the PID loops that are currently meaningful given our sensors.

  - yaw hold: REAL sensor feedback (VN-100 -> EKF). Yaw mixing is now
    structured with real signs based on confirmed thruster positions (see
    thruster_allocator_node.py), but still needs a bench test to confirm
    the sign direction before this is trusted closed-loop. Gains below
    default to 0 (does nothing) until that's done AND real tuning happens.

  - depth hold: NOT usable yet -- no pressure sensor is wired in, so
    /odometry/filtered's z is a meaningless placeholder right now. Written
    and wired up so enabling it later is a one-line gain change, not a
    rewrite.

Roll, pitch, and sway are deliberately NOT implemented:
  - roll/pitch: the 4 vertical thrusters' corner positions aren't
    confirmed yet -- see docs and TODOs in thruster_allocator_node.py.
  - sway: not physically possible with this thruster layout (differential
    drive, no lateral thrust capability).

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
        self.declare_parameter('yaw_kp', 0.0)
        self.declare_parameter('yaw_ki', 0.0)
        self.declare_parameter('yaw_kd', 0.0)
        self.declare_parameter('depth_kp', 0.0)
        self.declare_parameter('depth_ki', 0.0)
        self.declare_parameter('depth_kd', 0.0)
        
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

        self.current_yaw = 0.0
        self.current_depth = 0.0
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
        self.current_yaw = quaternion_to_yaw(msg.pose.pose.orientation)
        self.current_depth = msg.pose.pose.position.z

    # reads Setpoint msg from topic (desired state according to mission logic)
    def setpoint_callback(self, msg: Setpoint):
        self.setpoint_yaw = quaternion_to_yaw(msg.desired_pose.orientation)
        self.setpoint_depth = msg.desired_pose.position.z
        self.surge_command = msg.desired_velocity.linear.x

    def control_loop(self):
        now = self.get_clock().now()
        dt = (now - self.last_time).nanoseconds / 1e9
        self.last_time = now
        if dt <= 0.0:
            return

        yaw_error = shortest_angle_diff(self.setpoint_yaw, self.current_yaw)
        yaw_output = self.yaw_pid.update(setpoint=0.0, measurement=-yaw_error, dt=dt)

        depth_output = self.depth_pid.update(
            setpoint=self.setpoint_depth, measurement=self.current_depth, dt=dt)

        wrench = Wrench()
        wrench.force.x = self.surge_command   # open-loop, see class docstring
        wrench.force.y = 0.0                  # sway not achievable
        wrench.force.z = depth_output
        wrench.torque.x = 0.0                 # roll not implemented
        wrench.torque.y = 0.0                 # pitch not implemented
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
