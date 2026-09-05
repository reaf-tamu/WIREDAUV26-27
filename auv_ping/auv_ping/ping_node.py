#!/usr/bin/env python3
"""
Minimal driver for the Blue Robotics Ping Sonar, using Blue Robotics' own
official 'bluerobotics-ping' PyPI package (brping) directly -- not the
upstream ping_sonar_ros ROS2 wrapper.

We only need one number (altitude above the floor), so this skips
ping_sonar_ros's git submodule, its self-import PYTHONPATH quirk, and its
bundled RViz launch dependency entirely, in favor of just calling Blue
Robotics' already-written, already-tested library function directly and
publishing the result.

This is a request/response protocol, not a continuous stream like the
VN-100's ASCII sentences -- get_distance() actively asks the sensor for a
fresh reading and waits for a response, so this runs on a timer rather
than a tight read loop.

NOTE: min_range/max_range/field_of_view below are approximate, taken from
general Ping1D documentation, not independently verified against the
datasheet for our specific unit -- they're exposed as parameters
specifically so they're easy to correct later without touching code.
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Range

try:
    from brping import Ping1D
    HARDWARE_AVAILABLE = True
except ImportError:
    HARDWARE_AVAILABLE = False


class PingNode(Node):
    def __init__(self):
        super().__init__('ping_node')

        self.declare_parameter('port', '/dev/ping1d')
        self.declare_parameter('baud', 115200)
        self.declare_parameter('frame_id', 'ping1d')
        self.declare_parameter('rate_hz', 10.0)
        # TODO: verify these three against the actual Ping1D datasheet.
        self.declare_parameter('min_range_m', 0.5)
        self.declare_parameter('max_range_m', 30.0)
        self.declare_parameter('field_of_view_rad', 0.5236)  # ~30 degrees

        port = self.get_parameter('port').value
        baud = self.get_parameter('baud').value
        self.frame_id = self.get_parameter('frame_id').value
        self.min_range_m = self.get_parameter('min_range_m').value
        self.max_range_m = self.get_parameter('max_range_m').value
        self.field_of_view_rad = self.get_parameter('field_of_view_rad').value
        rate_hz = self.get_parameter('rate_hz').value

        self.pub = self.create_publisher(Range, '/ping1d/range', qos_profile_sensor_data)

        self.good_reads = 0
        self.bad_reads = 0

        self.ping = None
        if not HARDWARE_AVAILABLE:
            self.get_logger().warn(
                "brping not installed -- run: pip3 install bluerobotics-ping "
                "(commands will be logged, nothing published)")
        else:
            self.get_logger().info(f'Connecting to Ping Sonar on {port} @ {baud}')
            self.ping = Ping1D()
            self.ping.connect_serial(port, baud)
            if self.ping.initialize() is False:
                self.get_logger().error(
                    'Failed to initialize Ping Sonar -- check power/connection. '
                    'Node will keep retrying on each timer tick.')
                self.ping = None

        self.timer = self.create_timer(1.0 / rate_hz, self.read_loop)

    def read_loop(self):
        if self.ping is None:
            # Either brping isn't installed, or initialize() failed at
            # startup -- try to (re)initialize on every tick rather than
            # giving up permanently, in case the sensor gets connected or
            # powered on after this node already started.
            if HARDWARE_AVAILABLE:
                self.ping = Ping1D()
                self.ping.connect_serial(
                    self.get_parameter('port').value,
                    self.get_parameter('baud').value)
                if self.ping.initialize() is False:
                    self.ping = None
            return

        result = self.ping.get_distance()
        if not result or 'distance' not in result:
            self.bad_reads += 1
            return

        self.good_reads += 1

        msg = Range()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.frame_id
        msg.radiation_type = Range.ULTRASOUND
        msg.field_of_view = self.field_of_view_rad
        msg.min_range = self.min_range_m
        msg.max_range = self.max_range_m
        msg.range = result['distance'] / 1000.0  # brping reports mm; ROS wants meters

        self.pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = PingNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.get_logger().info(
            f'Shutting down. Good reads: {node.good_reads}, bad reads: {node.bad_reads}'
        )
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
