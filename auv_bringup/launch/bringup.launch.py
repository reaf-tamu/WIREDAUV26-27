"""Top-level launch file: brings up sensor drivers + state estimator + control.

Vision and mission launches are added here once those packages have real
nodes (see docs/architecture-roadmap.md for build order).

NOTE: verify driver launch filenames below against each driver's own
launch/ folder if anything fails to find, e.g.:
    ros2 pkg prefix <package> && ls $(ros2 pkg prefix <package>)/share/<package>/launch
and fix any that don't match.
"""

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare
from launch_ros.actions import Node
import math


def generate_launch_description():
    # --- VN-100 (orientation) ---
    vectornav_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([FindPackageShare('auv_vn100'), 'launch', 'vn100.launch.py'])
        ])
    )

    vectornav_mount_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='vectornav_mount_tf',
        arguments=[
            '--x', '0', '--y', '0', '--z', '0',
            '--roll', str(math.radians(-178)),
            '--pitch', str(math.radians(-3)),
            '--yaw', '0',
            '--frame-id', 'base_link',
            '--child-frame-id', 'vectornav',
        ]
    )

    # --- Ping Sonar (altitude) ---
    ping_sonar_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([FindPackageShare('auv_ping'), 'launch', 'ping.launch.py'])
        ])
    )

    # --- Bar02 pressure sensor (depth) ---
    pressure_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([FindPackageShare('auv_pressure'), 'launch', 'pressure.launch.py'])
        ])
    )

    # --- Wayfinder DVL (velocity) ---
    dvl_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([FindPackageShare('auv_dvl'), 'launch', 'dvl.launch.py'])
        ])
    )

    dvl_mount_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='dvl_mount_tf',
        arguments=[
            '--x', '0', '--y', '0', '--z', '0',
            '--roll', str(math.radians(180)),   # confirmed: mounted upside-down, facing the pool floor
            '--pitch', '0',
            # TODO: yaw is NOT yet verified -- see docs/sensors/dvl.md section 8.
            # Teledyne's own integration docs note the DVL's native X/Y axes can
            # be offset ~45 degrees from vehicle-forward depending on which beam
            # aligns with the bow. Verify empirically: drive forward at low power
            # in water, watch /dvl/odometry's vel_x vs vel_y. Motion almost
            # entirely in vel_x => yaw ~= 0. Split evenly between vel_x/vel_y =>
            # a ~45 degree correction is needed.
            '--yaw', '0',
            '--frame-id', 'base_link',
            '--child-frame-id', 'dvl',
        ]
    )

    # TODO: ZED SDK not installed yet. Uncomment once set up.
    # zed_launch = IncludeLaunchDescription(
    #     PythonLaunchDescriptionSource([
    #         PathJoinSubstitution([FindPackageShare('zed_wrapper'), 'launch', 'zed_camera.launch.py'])
    #     ]),
    #     launch_arguments={'camera_model': 'zedm'}.items()
    # )

    # --- State estimator ---
    localization_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([FindPackageShare('auv_localization'), 'launch', 'ekf.launch.py'])
        ])
    )

    # --- PID control + thruster allocation + hardware interface ---
    control_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([FindPackageShare('auv_control'), 'launch', 'control.launch.py'])
        ])
    )

    # TODO: bring these online once built
    # vision_launch = IncludeLaunchDescription(...)
    # mission_launch = IncludeLaunchDescription(...)

    return LaunchDescription([
        vectornav_launch,
        vectornav_mount_tf,
        ping_sonar_launch,
        pressure_launch,
        dvl_launch,
        dvl_mount_tf,
        localization_launch,
        control_launch,
    ])
