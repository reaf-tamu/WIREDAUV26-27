"""
thruster_allocator_node.py

Converts a desired Wrench into 8 individual thruster angle commands.

Confirmed thruster positions (horizontal/surge-yaw group):
  A1 = back-left   A4 = front-left
  M1 = back-right  M4 = front-right
  (A = port/left side, M = starboard/right side)

This is NOT a geometric allocation matrix built from full 3D thruster
positions -- we don't have confirmed corner positions for the 4 vertical
thrusters yet. Instead it reuses mixing validated by hand from the
original speeds.py, extended with the now-confirmed left/right structure:

  - Surge (force.x): confirmed from forward() -- A-group horizontal
    thrusters (A1, A4) get 90-k, M-group (M1, M4) get 90+k. Opposite signs
    because the two sides are mounted with mirrored prop orientation.
  - Heave (force.z): confirmed from down()/up() -- all 4 vertical
    thrusters move together as one group (no known-good independent
    control yet -- roll/pitch not implemented, see attitude_control_node.py).
  - Yaw (torque.z): structure now known -- A1/A4 (left side) move together,
    opposite M1/M4 (right side), same left/right split as surge. The SIGN
    (which side is + vs -) is still an assumption, not yet bench-verified.
    OFF by default (YAW_MIXING_VERIFIED = False).

    To enable it:
      1. Secure the vehicle on a bench/stand, thrusters at low power.
      2. Publish a small, isolated positive yaw wrench directly, e.g.:
         ros2 topic pub /auv/wrench geometry_msgs/msg/Wrench \
           "{torque: {z: 0.2}}"
      3. Observe which way it actually rotates.
      4. If it turns the expected direction, leave YAW_SIGN as-is. If it
         turns the OPPOSITE direction, flip all four YAW_SIGN values
         (multiply each by -1) -- don't adjust them individually, since
         they're structured as a matched left/right pair, not independent.
      5. Only then set YAW_MIXING_VERIFIED = True.

  - Roll, pitch, sway inputs are read but ignored -- not implemented.
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Wrench

from auv_msgs.msg import ThrusterCommands

NEUTRAL = 90.0

# Degrees of servo-angle swing a full-scale (+/-1.0) input produces.
# Matches the values already used successfully in testing (90 +/- 10) as a
# conservative starting point -- not derived from a thruster spec sheet.
# Widen deliberately, not by accident, once tested safe at this value.
SURGE_GAIN_DEG = 10.0
HEAVE_GAIN_DEG = 10.0
YAW_GAIN_DEG = 10.0

YAW_MIXING_VERIFIED = False  # see module docstring -- do not flip without a bench test

SURGE_SIGN = {'A1': -1, 'A4': -1, 'M1': +1, 'M4': +1}
HEAVE_SIGN = {'A2': +1, 'A3': +1, 'M2': +1, 'M3': +1}

# Structure known from confirmed positions (A = left, M = right): both
# thrusters on a side move together, opposite the other side, same split
# as SURGE_SIGN. Sign direction (+1 vs -1 per side) is still an assumption
# pending the bench test described above.
YAW_SIGN = {'A1': -1, 'A4': -1, 'M1': +1, 'M4': +1}


def clamp_angle(angle):
    # Conservative safety clamp matching the narrow range actually
    # exercised in prior testing (80-100).
    return max(60.0, min(120.0, angle))


class ThrusterAllocatorNode(Node):
    def __init__(self):
        super().__init__('thruster_allocator_node')
        self.create_subscription(Wrench, '/auv/wrench', self.wrench_callback, 10)
        self.pub = self.create_publisher(ThrusterCommands, '/auv/thruster_commands', 10)

    def wrench_callback(self, msg: Wrench):
        surge = msg.force.x
        heave = msg.force.z
        yaw = msg.torque.z if YAW_MIXING_VERIFIED else 0.0

        cmd = ThrusterCommands()
        cmd.a1 = clamp_angle(NEUTRAL + SURGE_SIGN['A1'] * SURGE_GAIN_DEG * surge
                              + YAW_SIGN['A1'] * YAW_GAIN_DEG * yaw)
        cmd.a4 = clamp_angle(NEUTRAL + SURGE_SIGN['A4'] * SURGE_GAIN_DEG * surge
                              + YAW_SIGN['A4'] * YAW_GAIN_DEG * yaw)
        cmd.m1 = clamp_angle(NEUTRAL + SURGE_SIGN['M1'] * SURGE_GAIN_DEG * surge
                              + YAW_SIGN['M1'] * YAW_GAIN_DEG * yaw)
        cmd.m4 = clamp_angle(NEUTRAL + SURGE_SIGN['M4'] * SURGE_GAIN_DEG * surge
                              + YAW_SIGN['M4'] * YAW_GAIN_DEG * yaw)

        cmd.a2 = clamp_angle(NEUTRAL + HEAVE_SIGN['A2'] * HEAVE_GAIN_DEG * heave)
        cmd.a3 = clamp_angle(NEUTRAL + HEAVE_SIGN['A3'] * HEAVE_GAIN_DEG * heave)
        cmd.m2 = clamp_angle(NEUTRAL + HEAVE_SIGN['M2'] * HEAVE_GAIN_DEG * heave)
        cmd.m3 = clamp_angle(NEUTRAL + HEAVE_SIGN['M3'] * HEAVE_GAIN_DEG * heave)

        self.pub.publish(cmd)


def main(args=None):
    rclpy.init(args=args)
    node = ThrusterAllocatorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
