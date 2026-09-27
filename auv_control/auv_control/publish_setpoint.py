#!/usr/bin/env python3
"""Manual testing tool: publish a Setpoint offset from the vehicle's
current roll/pitch/yaw, for bench-testing PID loops without a mission
running.

Usage: ros2 run auv_control publish_setpoint <roll|pitch|yaw> <degrees offset>
"""
import sys, math
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from auv_msgs.msg import Setpoint


def quat_to_rpy(q):
    sinr_cosp = 2.0 * (q.w * q.x + q.y * q.z)
    cosr_cosp = 1.0 - 2.0 * (q.x * q.x + q.y * q.y)
    roll = math.atan2(sinr_cosp, cosr_cosp)

    sinp = 2.0 * (q.w * q.y - q.z * q.x)
    sinp = max(-1.0, min(1.0, sinp))
    pitch = math.asin(sinp)

    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    yaw = math.atan2(siny_cosp, cosy_cosp)
    return roll, pitch, yaw


def rpy_to_quat(roll, pitch, yaw):
    cy, sy = math.cos(yaw * 0.5), math.sin(yaw * 0.5)
    cp, sp = math.cos(pitch * 0.5), math.sin(pitch * 0.5)
    cr, sr = math.cos(roll * 0.5), math.sin(roll * 0.5)
    w = cr * cp * cy + sr * sp * sy
    x = sr * cp * cy - cr * sp * sy
    y = cr * sp * cy + sr * cp * sy
    z = cr * cp * sy - sr * sp * cy
    return x, y, z, w


def main(args=None):
    if len(sys.argv) < 3:
        print("Usage: ros2 run auv_control publish_setpoint <roll|pitch|yaw> <degrees offset>")
        return
    axis = sys.argv[1].lower()
    offset_deg = float(sys.argv[2])
    if axis not in ('roll', 'pitch', 'yaw'):
        print("axis must be roll, pitch, or yaw")
        return

    rclpy.init(args=args)
    node = Node('setpoint_publisher')
    current = {'val': None}

    def odom_cb(msg):
        current['val'] = quat_to_rpy(msg.pose.pose.orientation)

    node.create_subscription(Odometry, '/odometry/filtered', odom_cb, 10)
    pub = node.create_publisher(Setpoint, '/auv/setpoint', 10)

    while current['val'] is None:
        rclpy.spin_once(node, timeout_sec=0.5)
        print("Waiting for /odometry/filtered...")

    roll, pitch, yaw = current['val']
    original = {'roll': roll, 'pitch': pitch, 'yaw': yaw}
    original[axis] += math.radians(offset_deg)

    msg = Setpoint()
    qx, qy, qz, qw = rpy_to_quat(original['roll'], original['pitch'], original['yaw'])
    msg.desired_pose.orientation.x = qx
    msg.desired_pose.orientation.y = qy
    msg.desired_pose.orientation.z = qz
    msg.desired_pose.orientation.w = qw
    msg.desired_velocity.linear.x = 0.0
    msg.use_altitude_hold = False

    for _ in range(10):
        pub.publish(msg)
        rclpy.spin_once(node, timeout_sec=0.1)

    before = {'roll': roll, 'pitch': pitch, 'yaw': yaw}[axis]
    after = original[axis]
    print(f"{axis}: current {math.degrees(before):.1f} deg -> "
          f"target {math.degrees(after):.1f} deg (offset {offset_deg})")

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
