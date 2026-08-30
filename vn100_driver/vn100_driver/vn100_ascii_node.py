#!/usr/bin/env python3
"""
Minimal ASCII-mode driver for the VectorNav VN-100.

Reads $VNYMR sentences directly over serial (no binary-mode reconfiguration,
no vnproglib) and publishes sensor_msgs/Imu on /vectornav/imu.

Only handles $VNYMR (yaw/pitch/roll, mag, accel, gyro). If GPS/INS/raw
uncompensated data are ever needed later, this would need extending, or
the sensor would need to go back on the full binary driver.

NOTE: orientation is published in the sensor's native output convention
(degrees, ZYX yaw-pitch-roll), with NO NED->ENU frame conversion applied.
This has NOT been verified against ROS's ENU/right-hand-rule convention --
before trusting this in the EKF, rotate the sensor to known headings
(compass N/E/S/W) and confirm the published quaternion matches what you'd
expect. If it's off, the fix is almost certainly in euler_deg_to_quaternion()
below.
"""

import math

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Imu
import serial


def euler_deg_to_quaternion(yaw_deg, pitch_deg, roll_deg):
    """ZYX (yaw, pitch, roll) Euler angles in degrees -> quaternion (x,y,z,w)."""
    yaw = math.radians(yaw_deg)
    pitch = math.radians(pitch_deg)
    roll = math.radians(roll_deg)

    cy = math.cos(yaw * 0.5)
    sy = math.sin(yaw * 0.5)
    cp = math.cos(pitch * 0.5)
    sp = math.sin(pitch * 0.5)
    cr = math.cos(roll * 0.5)
    sr = math.sin(roll * 0.5)

    w = cr * cp * cy + sr * sp * sy
    x = sr * cp * cy - cr * sp * sy
    y = cr * sp * cy + sr * cp * sy
    z = cr * cp * sy - sr * sp * cy
    return x, y, z, w


class VN100AsciiNode(Node):
    def __init__(self):
        super().__init__('vn100_ascii_node')

        self.declare_parameter('port', '/dev/vectornav')
        self.declare_parameter('baud', 115200)
        self.declare_parameter('frame_id', 'vectornav')

        port = self.get_parameter('port').value
        baud = self.get_parameter('baud').value
        self.frame_id = self.get_parameter('frame_id').value

        self.pub = self.create_publisher(Imu, '/vectornav/imu', qos_profile_sensor_data)

        self.get_logger().info(f'Opening {port} @ {baud}')
        self.serial = serial.Serial(port, baud, timeout=1.0)

        self.bad_lines = 0
        self.good_lines = 0

        self.timer = self.create_timer(0.001, self.read_loop)

    def read_loop(self):
        try:
            raw = self.serial.readline()
        except serial.SerialException as e:
            self.get_logger().error(f'Serial read failed: {e}')
            return

        if not raw:
            return

        try:
            line = raw.decode('ascii', errors='strict').strip()
        except UnicodeDecodeError:
            self.bad_lines += 1
            return

        if not line.startswith('$VNYMR'):
            return

        if '*' in line:
            line = line.split('*')[0]

        fields = line.split(',')
        # $VNYMR,Yaw,Pitch,Roll,MagX,MagY,MagZ,AccelX,AccelY,AccelZ,GyroX,GyroY,GyroZ
        if len(fields) != 13:
            self.bad_lines += 1
            return

        try:
            yaw, pitch, roll = (float(fields[1]), float(fields[2]), float(fields[3]))
            accel_x, accel_y, accel_z = (float(fields[7]), float(fields[8]), float(fields[9]))
            gyro_x, gyro_y, gyro_z = (float(fields[10]), float(fields[11]), float(fields[12]))
        except ValueError:
            self.bad_lines += 1
            return

        self.good_lines += 1

        msg = Imu()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.frame_id

        qx, qy, qz, qw = euler_deg_to_quaternion(yaw, pitch, roll)
        msg.orientation.x = qx
        msg.orientation.y = qy
        msg.orientation.z = qz
        msg.orientation.w = qw

        msg.angular_velocity.x = gyro_x
        msg.angular_velocity.y = gyro_y
        msg.angular_velocity.z = gyro_z

        msg.linear_acceleration.x = accel_x
        msg.linear_acceleration.y = accel_y
        msg.linear_acceleration.z = accel_z

        for cov in (msg.orientation_covariance, msg.angular_velocity_covariance,
                    msg.linear_acceleration_covariance):
            cov[0] = cov[4] = cov[8] = 0.01

        self.pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = VN100AsciiNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.get_logger().info(
            f'Shutting down. Good lines: {node.good_lines}, bad lines: {node.bad_lines}'
        )
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
