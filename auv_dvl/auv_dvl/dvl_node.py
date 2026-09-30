#!/usr/bin/env python3
"""
Minimal driver for the Teledyne Wayfinder DVL, using Teledyne's own
official Python SDK directly (already confirmed working in a standalone
Windows/VM test -- see auv_dvl/README.md). This node is the Linux/ROS2
port of that same tested logic, not a reimplementation of the protocol.

IMPORTANT -- coordinate frame NOT yet resolved:
vel_x/vel_y/vel_z below are published exactly as the DVL SDK reports
them, in the DVL's own native axis convention. This has NOT been
verified against our ENU convention (the same class of issue the VN-100
had before its mounting transform was figured out -- see
docs/sensors/vn100.md section 8). Do not assume vel_x maps directly to
"forward" without confirming the DVL's actual mounting orientation and
native frame (check the Wayfinder manual for whether it reports in
FRD/NED-style axes) -- this is explicitly flagged as open in our own
auv_dvl/README.md's "Next Steps" already.

Port note: the original Windows test used "COM3". On the Jetson this
will be a Linux device (e.g. /dev/ttyUSB0) -- give it a udev rule for a
stable name (see docs/concepts/udev-rules.md), same as the VN-100 and
Ping Sonar, rather than relying on a raw port number that can shift.

Only publishes when data.is_valid is True -- same "don't pass along data
the sensor itself flags as untrustworthy" pattern used for the Ping
Sonar's confidence filtering.
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from nav_msgs.msg import Odometry

try:
    from dvl.dvl import Dvl
    HARDWARE_AVAILABLE = True
except ImportError:
    HARDWARE_AVAILABLE = False


class DvlNode(Node):
    def __init__(self):
        super().__init__('dvl_node')

        self.declare_parameter('port', '/dev/dvl')
        self.declare_parameter('baud', 115200)
        self.declare_parameter('frame_id', 'dvl')

        self.frame_id = self.get_parameter('frame_id').value

        self.odom_pub = self.create_publisher(Odometry, '/dvl/odometry', qos_profile_sensor_data)

        self.good_reads = 0
        self.invalid_reads = 0

        self.dvl = None
        if not HARDWARE_AVAILABLE:
            self.get_logger().warn(
                "Teledyne 'dvl' driver not installed -- see auv_dvl/README.md for the "
                "vendor-download install step (not a public pip/git package). "
                "Node will stay idle.")
            return

        port = self.get_parameter('port').value
        baud = self.get_parameter('baud').value
        self.get_logger().info(f'Connecting to DVL on {port} @ {baud}')

        self.dvl = Dvl()
        if not self.dvl.connect(port, baud):
            self.get_logger().error(f'Could not connect to DVL: {self.dvl.last_err}')
            self.dvl = None
            return

        self.get_logger().info('Connected to DVL')

        # Log real identifying info at startup, same as we do for other
        # sensors -- catches "connected to the wrong thing" early.
        try:
            self.dvl.get_system()
            self.get_logger().info(f'DVL system info: {self.dvl.system_info}')
        except Exception as e:
            self.get_logger().warn(f'Could not read DVL system info: {e}')

        self.dvl.register_ondata_callback(self.on_data)

        if not self.dvl.exit_command_mode():
            self.get_logger().error(f'Could not start DVL pinging: {self.dvl.last_err}')
            self.dvl.disconnect()
            self.dvl = None

    def on_data(self, data, obj):
        if not data.is_valid:
            self.invalid_reads += 1
            return

        self.good_reads += 1

        msg = Odometry()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.frame_id

        # NOT yet confirmed to be in our ENU convention -- see module docstring.
        msg.twist.twist.linear.x = data.vel_x
        msg.twist.twist.linear.y = data.vel_y
        msg.twist.twist.linear.z = data.vel_z

        self.odom_pub.publish(msg)

    def destroy_node(self):
        if self.dvl is not None:
            self.get_logger().info('Shutting down -- returning DVL to command mode')
            self.dvl.enter_command_mode()
            self.dvl.unregister_all_callbacks()
            self.dvl.disconnect()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = DvlNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.get_logger().info(
            f'Good reads: {node.good_reads}, invalid reads: {node.invalid_reads}'
        )
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
