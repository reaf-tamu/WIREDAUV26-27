"""
thruster_allocator_node.py

Converts a desired Wrench into 8 individual thruster angle commands.

Confirmed thruster positions (horizontal/surge-yaw group):
  A1 = back-left   A4 = front-left
  M1 = back-right  M4 = front-right
  (A = port/left side, M = starboard/right side)

Confirmed thruster positions (vertical/heave-roll-pitch group):
  A3 = front-left   A2 = back-left
  M3 = front-right  M2 = back-right

  - Surge (force.x): confirmed from forward() -- A-group horizontal
    thrusters (A1, A4) get 90-k, M-group (M1, M4) get 90+k. Opposite signs
    because the two sides are mounted with mirrored prop orientation.
  - Yaw (torque.z): structure known -- A1/A4 (left side) move together,
    opposite M1/M4 (right side), same left/right split as surge. Sign
    bench-verified -- see YAW_MIXING_VERIFIED.
  - Heave (force.z): confirmed from down()/up() -- all 4 vertical
    thrusters move together as one group (unlike the horizontal group,
    all four use the SAME sign -- down()/up() commanded identical values
    across A and M).
  - Roll (torque.x): structure now known -- left thrusters (A2, A3) oppose
    right thrusters (M2, M3), same left/right split as surge/yaw. Sign is
    NOT bench-verified yet -- OFF by default (ROLL_MIXING_VERIFIED = False).
  - Pitch (torque.y): structure now known -- front thrusters (A3, M3)
    oppose back thrusters (A2, M2). Sign is NOT bench-verified yet -- OFF
    by default (PITCH_MIXING_VERIFIED = False).

  To enable roll or pitch:
    1. Secure the vehicle on a bench/stand, thrusters at low power.
    2. Publish a small, isolated wrench, e.g. for roll:
       ros2 topic pub /auv/wrench geometry_msgs/msg/Wrench \
         "{torque: {x: 0.2}}"
       (use torque: {y: 0.2} for pitch)
    3. Observe which way it actually rotates.
    4. If it matches the expected direction (positive roll = right side
       down; positive pitch = nose down, per REP-103/right-hand rule),
       leave the SIGN dict as-is. If backwards, flip ALL FOUR values in
       that SIGN dict together (multiply each by -1) -- they're a matched
       set, not independent.
    5. Only then set the corresponding _MIXING_VERIFIED flag to True.

  Do roll and pitch as two SEPARATE bench tests -- don't assume one
  confirms the other, since they use different thruster pairings.

  Sway is not implemented -- not physically possible with this thruster
  layout.
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Wrench

from auv_msgs.msg import ThrusterCommands

NEUTRAL = 90.0

# Degrees of servo-angle swing a full-scale (+/-1.0) input produces.
# Matches values already used successfully in testing (90 +/- 10) as a
# conservative starting point -- not derived from a thruster spec sheet.
SURGE_GAIN_DEG = 10.0
HEAVE_GAIN_DEG = 10.0
YAW_GAIN_DEG = 10.0
ROLL_GAIN_DEG = 10.0
PITCH_GAIN_DEG = 10.0

YAW_MIXING_VERIFIED = False    # bench test yaw before flipping this
ROLL_MIXING_VERIFIED = False   # bench test roll before flipping this
PITCH_MIXING_VERIFIED = False  # bench test pitch before flipping this

SURGE_SIGN = {'A1': -1, 'A4': -1, 'M1': +1, 'M4': +1}
YAW_SIGN = {'A1': -1, 'A4': -1, 'M1': +1, 'M4': +1}

HEAVE_SIGN = {'A2': +1, 'A3': +1, 'M2': +1, 'M3': +1}
# Left (A2, A3) vs right (M2, M3) -- arbitrary starting sign, unverified.
ROLL_SIGN = {'A2': +1, 'A3': +1, 'M2': -1, 'M3': -1}
# Front (A3, M3) vs back (A2, M2) -- arbitrary starting sign, unverified.
PITCH_SIGN = {'A2': -1, 'A3': +1, 'M2': -1, 'M3': +1}


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
        roll = msg.torque.x if ROLL_MIXING_VERIFIED else 0.0
        pitch = msg.torque.y if PITCH_MIXING_VERIFIED else 0.0

        cmd = ThrusterCommands()

        # Horizontal group: surge + yaw
        cmd.a1 = clamp_angle(NEUTRAL + SURGE_SIGN['A1'] * SURGE_GAIN_DEG * surge
                              + YAW_SIGN['A1'] * YAW_GAIN_DEG * yaw)
        cmd.a4 = clamp_angle(NEUTRAL + SURGE_SIGN['A4'] * SURGE_GAIN_DEG * surge
                              + YAW_SIGN['A4'] * YAW_GAIN_DEG * yaw)
        cmd.m1 = clamp_angle(NEUTRAL + SURGE_SIGN['M1'] * SURGE_GAIN_DEG * surge
                              + YAW_SIGN['M1'] * YAW_GAIN_DEG * yaw)
        cmd.m4 = clamp_angle(NEUTRAL + SURGE_SIGN['M4'] * SURGE_GAIN_DEG * surge
                              + YAW_SIGN['M4'] * YAW_GAIN_DEG * yaw)

        # Vertical group: heave + roll + pitch, all summed onto the same neutral baseline
        cmd.a2 = clamp_angle(NEUTRAL + HEAVE_SIGN['A2'] * HEAVE_GAIN_DEG * heave
                              + ROLL_SIGN['A2'] * ROLL_GAIN_DEG * roll
                              + PITCH_SIGN['A2'] * PITCH_GAIN_DEG * pitch)
        cmd.a3 = clamp_angle(NEUTRAL + HEAVE_SIGN['A3'] * HEAVE_GAIN_DEG * heave
                              + ROLL_SIGN['A3'] * ROLL_GAIN_DEG * roll
                              + PITCH_SIGN['A3'] * PITCH_GAIN_DEG * pitch)
        cmd.m2 = clamp_angle(NEUTRAL + HEAVE_SIGN['M2'] * HEAVE_GAIN_DEG * heave
                              + ROLL_SIGN['M2'] * ROLL_GAIN_DEG * roll
                              + PITCH_SIGN['M2'] * PITCH_GAIN_DEG * pitch)
        cmd.m3 = clamp_angle(NEUTRAL + HEAVE_SIGN['M3'] * HEAVE_GAIN_DEG * heave
                              + ROLL_SIGN['M3'] * ROLL_GAIN_DEG * roll
                              + PITCH_SIGN['M3'] * PITCH_GAIN_DEG * pitch)

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
