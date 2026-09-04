"""
thruster_interface_node.py

The only node here that actually talks to hardware -- the ROS2-ified
version of the original motors.py. Kept separate from the allocator so its
mixing logic can be tested without the physical PCA9685 board attached.
"""

import rclpy
from rclpy.node import Node

from auv_msgs.msg import ThrusterCommands

try:
    from adafruit_servokit import ServoKit
    HARDWARE_AVAILABLE = True
except ImportError:
    HARDWARE_AVAILABLE = False

NEUTRAL = 90.0

# Channel assignments -- copied directly from the original motors.py.
CHANNELS = {
    'a1': 12, 'a2': 13, 'a3': 14, 'a4': 15,
    'm1': 2, 'm2': 3, 'm3': 4, 'm4': 5,
}


class ThrusterInterfaceNode(Node):
    def __init__(self):
        super().__init__('thruster_interface_node')

        if HARDWARE_AVAILABLE:
            self.kit = ServoKit(channels=16)
            self.get_logger().info('PCA9685 detected, driving real hardware.')
        else:
            self.kit = None
            self.get_logger().warn(
                'adafruit_servokit not available -- commands will be logged, not sent.')

        self._last_sent = {name: None for name in CHANNELS}
        self.initialize_escs()

        self.create_subscription(
            ThrusterCommands, '/auv/thruster_commands', self.command_callback, 10)

    def initialize_escs(self):
        self.get_logger().info(
            'Initializing thrusters -- should hear two beeps after power cycle')
        for name in CHANNELS:
            self._send(name, NEUTRAL)

    def _send(self, name, angle):
        if self._last_sent[name] == angle:
            return
        self._last_sent[name] = angle
        if self.kit is not None:
            self.kit.servo[CHANNELS[name]].angle = angle

    def command_callback(self, msg: ThrusterCommands):
        self._send('a1', msg.a1)
        self._send('a2', msg.a2)
        self._send('a3', msg.a3)
        self._send('a4', msg.a4)
        self._send('m1', msg.m1)
        self._send('m2', msg.m2)
        self._send('m3', msg.m3)
        self._send('m4', msg.m4)

    def destroy_node(self):
        # Safety: return every thruster to neutral on shutdown, unlike the
        # original script, which only stopped motors on a normal mission
        # finish -- not on Ctrl+C or a crash.
        self.get_logger().info('Shutting down -- returning all thrusters to neutral')
        for name in CHANNELS:
            self._last_sent[name] = None
            self._send(name, NEUTRAL)
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = ThrusterInterfaceNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
