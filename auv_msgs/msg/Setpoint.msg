# A single desired-state command sent from the mission planner to the controllers.
# See auv_msgs/README.md for how this is used.

geometry_msgs/Pose desired_pose        # target position + orientation
geometry_msgs/Twist desired_velocity   # target velocity (used if use_velocity_control is true)
bool use_velocity_control              # true = hold desired_velocity, false = hold desired_pose
bool use_altitude_hold                 # defaults to false
