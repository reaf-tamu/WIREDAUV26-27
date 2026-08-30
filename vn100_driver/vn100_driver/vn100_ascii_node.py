#!/usr/bin/env python3
"""
Minimal ASCII-mode driver for the VectorNav VN-100.

Reads $VNYMR sentences directly over serial (no binary-mode reconfiguration,
no vnproglib) and publishes sensor_msgs/Imu on /vectornav/imu.

Only handles $VNYMR (yaw/pitch/roll, mag, accel, gyro). If GPS/INS/raw
uncompensated data are ever needed later, this would need extending, or
the sensor would need to go back on the full binary driver.

"""

import math

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Imu
import serial

"""
Function: Convert euler angles to quaternions
Purpose: Euler angles are intuitive to read, but mathematically flawed
    - gimbal lock -> when pitch approches 90*, yaw and roll axes become parallel, lose degree of freedom
                     small changes in orienation require large, discontinuous jumps in yaw/roll numbers
                     often get stuck or nonsensical results
Instead of doing math with Euler angles, it is good practice to convert them to quaternions, which represents
  rotation as 4 numbers (x,y,z,w) in a way that has no singularities.
  EKF and ROS's premade IMU sensor messages want quaternions so they can safely do this math without worrying about gimbal lock
"""
def euler_deg_to_quaternion(yaw_deg, pitch_deg, roll_deg):
    """ZYX (yaw, pitch, roll) Euler angles in degrees -> quaternion (x,y,z,w)."""

    # The VN-100 gives us angles in degrees, but trig function in Python's math module expects radians
    yaw = math.radians(yaw_deg)
    pitch = math.radians(pitch_deg)
    roll = math.radians(roll_deg)

    # Convert Euler angles to quaternions
    # Look at docs/concepts/euler-quaternions.md 
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

        # default parameter values
        self.declare_parameter('port', '/dev/vectornav')
        self.declare_parameter('baud', 115200)
        self.declare_parameter('frame_id', 'vectornav')
        
        # uses parameter values are declared in vn100.lauch.py (otherwise defaults declared above)
        port = self.get_parameter('port').value
        baud = self.get_parameter('baud').value
        self.frame_id = self.get_parameter('frame_id').value

        # creates publisher
        # declares topic /vectornav/imu that other nodes can subscribe to get vectornav data
        # qos_profile_sensor_data -> quality of service setting that accepts fast arriving sensor data
        #        tolerating occational missing message for high speed
        self.pub = self.create_publisher(Imu, '/vectornav/imu', qos_profile_sensor_data)

        # Displays port and baud rate on terminal to confirm correct parameters
        self.get_logger().info(f'Opening {port} @ {baud}')
        # Opens serial connection to sensor, times out if returns empty after 1s
        self.serial = serial.Serial(port, baud, timeout=1.0)

        # health counters - printed at shutdown to confirm real, correct data was recieved
        # debugging purposes
        self.bad_lines = 0
        self.good_lines = 0

        # ROS2 timer calls read_loop every 1ms
        # Reads data every 1ms (1kHz), even tho sensor publishes data ~39Hz
        # Poll faster to get new data as soon as it arrives, can't miss or introduce unnecessary lag
        self.timer = self.create_timer(0.001, self.read_loop)

    def read_loop(self):
        try:
            # read next complete line from serial port
            raw = self.serial.readline()
        except serial.SerialException as e:
            self.get_logger().error(f'Serial read failed: {e}')
            return

        # no new line (common, since we are sampling much faster than data is published)
        if not raw:
            return

        try:
            # decode ASCII raw bytes representation to a string 
            line = raw.decode('ascii', errors='strict').strip()
        except UnicodeDecodeError:
            # occasional bad lines expected - sensors prioritize speed over quality
            # don't want to exit code, but report so we can make sure we aren't getting a concerningly large number
            self.bad_lines += 1
            return

        # driver is only coded to understand $VNYMR style messages (ASCII code)
        # ignore any line read that does not match this format
        if not line.startswith('$VNYMR'):
            return
            
        # chops off check sum, part of data we don't care about
        if '*' in line:
            line = line.split('*')[0]

        # data is separated by commas, should have 13 fields (tag + 12 data points listed below)
        fields = line.split(',')
        # $VNYMR,Yaw,Pitch,Roll,MagX,MagY,MagZ,AccelX,AccelY,AccelZ,GyroX,GyroY,GyroZ
        if len(fields) != 13:
            self.bad_lines += 1
            return

        try:
            # convert string data to floats for the data points we use (don't use magnetometer)
            yaw, pitch, roll = (float(fields[1]), float(fields[2]), float(fields[3]))
            accel_x, accel_y, accel_z = (float(fields[7]), float(fields[8]), float(fields[9]))
            gyro_x, gyro_y, gyro_z = (float(fields[10]), float(fields[11]), float(fields[12]))
        except ValueError:
            self.bad_lines += 1
            return
            
        # if we made it to this point, we officially have a good line of data! Yay!
        self.good_lines += 1

        # Build ROS message
        msg = Imu()
        # ROS messages that represent sensor data need a timestamp (when reading occurred) 
        #    and a frame id (which cordinate frame it is relative to)
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.frame_id

        # use our euler to quaternion function from earlier to convert the euler angles read in from 
        #    the VectorNav to the quaternion representation that the message needs
        qx, qy, qz, qw = euler_deg_to_quaternion(-yaw, -pitch, roll)

        # asssign sensor readings to correct message component
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

        # TODO - fill in palce holder confidence values
        # see process-noise discussion in Kalman filter doc
        # Determines how much these readings should be trusted and influence our state estimation
        for cov in (msg.orientation_covariance, msg.angular_velocity_covariance,
                    msg.linear_acceleration_covariance):
            cov[0] = cov[4] = cov[8] = 0.01

        # publish message to the /vectornav/imu topic so other nodes can read it
        #    EKF node subscribes to this tehe
        self.pub.publish(msg)


def main(args=None):
    rclpy.init(args=args) # starts up ROS2
    node = VN100AsciiNode() # create node
    try:
        rclpy.spin(node) # keeps node alive, processes callbacks, until interrupted
    except KeyboardInterrupt:
        pass
    finally:
        node.get_logger().info(
            f'Shutting down. Good lines: {node.good_lines}, bad lines: {node.bad_lines}'
        )
        node.destroy_node() # clean up node
        rclpy.shutdown() # tear down ROS2


if __name__ == '__main__':
    main()
