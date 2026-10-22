"""
thruster_interface_node.py

The only node here that actually talks to hardware -- the ROS2-ified
version of the original motors.py. Kept separate from the allocator so its
mixing logic can be tested without the physical PCA9685 board attached.

Also drives the gripper servo on a free PCA9685 channel. The gripper lives
in this node (not its own node) because creating a second ServoKit resets
the PCA9685 and would briefly cut the signal to every thruster.
"""

import rclpy
from rclpy.node import Node

from auv_msgs.msg import ThrusterCommands
from std_msgs.msg import Float32

try:
    from adafruit_servokit import ServoKit
    HARDWARE_AVAILABLE = True
except ImportError:
    HARDWARE_AVAILABLE = False

NEUTRAL = 90.0

# Channel assignments -- copied directly from the original motors.py.
CHANNELS = {
    'a1': 12, 'a2': 13, 'a3': 14, 'a4': 15,
    'm1': 8, 'm2': 9, 'm3': 10, 'm4': 11,
}

# --- Gripper servo (Hitec D954SW in Blue Trail SER-2000 housing) ---
GRIPPER_CH = 0                 # any free channel 0-7
GRIPPER_MIN_US = 800           # D954SW spec pulse range
GRIPPER_MAX_US = 2200
# Positions as a fraction of the pulse range (0.0 = 800 us, 1.0 = 2200 us).
# PLACEHOLDERS -- calibrate on the bench before use. CLOSED should just grip
# the object, not drive the fingers into a hard stop (stalling for more than
# 5-10 s can destroy the servo).
GRIPPER_OPEN = 0 # PLACEHOLDER
GRIPPER_CLOSED = 0 #PLACEHOLDER


class ThrusterInterfaceNode(Node):
    def __init__(self):
        super().__init__('thruster_interface_node')

        # check that servo kit is installed, otherwise PCA9685 can't communicate with thrusters
        if HARDWARE_AVAILABLE:
            self.kit = ServoKit(channels=16)  # default 50 Hz, fine for ESCs and the servo
            self.get_logger().info('PCA9685 detected, driving real hardware.')
        else:
            self.kit = None
            self.get_logger().warn(
                'adafruit_servokit not available -- commands will be logged, not sent.')

        self._last_sent = {name: None for name in CHANNELS}
        self.initialize_escs()

        # gripper setup: match the servo's pulse range, then start open
        if self.kit is not None:
            self.kit.servo[GRIPPER_CH].set_pulse_width_range(
                GRIPPER_MIN_US, GRIPPER_MAX_US)
        self._gripper_last = None
        self.set_gripper(GRIPPER_OPEN)

        # subscribes to thruster commands
        self.create_subscription(
            ThrusterCommands, '/auv/thruster_commands', self.command_callback, 10)

        # subscribes to gripper commands (fraction 0.0-1.0, clamped to calibrated limits)
        self.create_subscription(
            Float32, '/auv/gripper_command', self.gripper_callback, 10)

    def initialize_escs(self):
        self.get_logger().info(
            'Initializing thrusters -- should hear two beeps after power cycle')
        for name in CHANNELS:
            self._send(name, NEUTRAL)

    def _send(self, name, angle):
        # if no change in commmand, don't send to thrusters
        if self._last_sent[name] == angle:
            return
        self._last_sent[name] = angle
        if self.kit is not None:
            self.kit.servo[CHANNELS[name]].angle = angle # send new command to thrusters

    # send command on auv/thruster_commands to thrusters
    def command_callback(self, msg: ThrusterCommands):
        self._send('a1', msg.a1)
        self._send('a2', msg.a2)
        self._send('a3', msg.a3)
        self._send('a4', msg.a4)
        self._send('m1', msg.m1)
        self._send('m2', msg.m2)
        self._send('m3', msg.m3)
        self._send('m4', msg.m4)

    def set_gripper(self, fraction):
        # clamp to the calibrated limits so a bad command can't stall the servo
        lo, hi = sorted((GRIPPER_OPEN, GRIPPER_CLOSED))
        clamped = max(lo, min(hi, fraction))
        if clamped != fraction:
            self.get_logger().warn(
                f'Gripper command {fraction:.3f} clamped to {clamped:.3f}')
        if clamped == self._gripper_last:
            return
        self._gripper_last = clamped
        if self.kit is not None:
            self.kit.servo[GRIPPER_CH].fraction = clamped
        else:
            self.get_logger().info(f'[no hardware] gripper -> {clamped:.3f}')

    def gripper_callback(self, msg: Float32):
        self.set_gripper(msg.data)

    # STOPS ALL THRUSTERS when this node quits (thrusters should never be left running
    def destroy_node(self):
        # Safety: return every thruster to neutral on shutdown, unlike the
        # original script, which only stopped motors on a normal mission
        # finish -- not on Ctrl+C or a crash.
        self.get_logger().info('Shutting down -- returning all thrusters to neutral')
        for name in CHANNELS:
            self._last_sent[name] = None
            self._send(name, NEUTRAL)

        # Open the gripper so the servo isn't left squeezing at stall.
        self.get_logger().info('Shutting down -- opening gripper')
        self._gripper_last = None
        self.set_gripper(GRIPPER_OPEN)
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
