"""Top-level launch file: brings up sensor drivers + state estimator.

Control, vision, and mission launches are added here once those
packages have real nodes (see docs/architecture-roadmap.md for build order).

NOTE: verify the driver launch filenames below against each driver's own
launch/ folder once built, e.g. ,
and fix any that don't match.
"""

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    vectornav_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([FindPackageShare('vn100_driver'), 'launch', 'vn100.launch.py'])
        ])
    )

    ping_sonar_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([FindPackageShare('ping_sonar_ros'), 'launch', 'ping_sonar.launch.py'])
        ])
    )

    # TODO: ZED SDK not installed yet. Uncomment once set up
    #zed_launch = IncludeLaunchDescription(
    #    PythonLaunchDescriptionSource([
    #        PathJoinSubstitution([FindPackageShare('zed_wrapper'), 'launch', 'zed_camera.launch.py'])
    #    ]),
    #    launch_arguments={'camera_model': 'zedm'}.items()
    #)

    # TODO: pressure sensor not wired yet. Uncomment once ms5837_bar_ros is on the vehicle.
    # pressure_launch = IncludeLaunchDescription(
    #     PythonLaunchDescriptionSource([
    #         PathJoinSubstitution([FindPackageShare('ms5837_bar_ros'), 'launch', 'ms5837.launch.py'])
    #     ])
    # )

    localization_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([FindPackageShare('auv_localization'), 'launch', 'ekf.launch.py'])
        ])
    )

    # TODO: bring these online at their respective build stages
    # control_launch = IncludeLaunchDescription(...)
    # vision_launch = IncludeLaunchDescription(...)
    # mission_launch = IncludeLaunchDescription(...)

    return LaunchDescription([
        vectornav_launch,
        ping_sonar_launch,
        #zed_launch,
        localization_launch,
    ])
