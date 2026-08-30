#!/bin/bash
set -e

# ---------- auv_control, auv_vision, auv_mission: minimal skeleton for now ----------
declare -A descs=(
  [auv_control]="PID control loops and thruster allocation."
  [auv_vision]="Combines YOLO detections with depth data into 3D target poses for the mission planner."
  [auv_mission]="Mission planner: decides the vehicle's current goal and publishes setpoints to auv_control."
)

for pkg in "${!descs[@]}"; do
  mkdir -p "$pkg/$pkg" "$pkg/resource"
  touch "$pkg/$pkg/__init__.py"
  touch "$pkg/resource/$pkg"

  cat > "$pkg/setup.py" << PYEOF
from setuptools import find_packages, setup

package_name = '$pkg'

setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Your Name',
    maintainer_email='you@example.com',
    description="${descs[$pkg]}",
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
        ],
    },
)
PYEOF

  cat > "$pkg/setup.cfg" << CFGEOF
[develop]
script_dir=\$base/lib/$pkg
[install]
install_scripts=\$base/lib/$pkg
CFGEOF

  echo "Created minimal skeleton for $pkg"
done

mkdir -p auv_control/config
touch auv_control/config/.gitkeep

# ---------- auv_bringup: real launch file ----------
mkdir -p auv_bringup/auv_bringup auv_bringup/resource auv_bringup/launch
touch auv_bringup/auv_bringup/__init__.py
touch auv_bringup/resource/auv_bringup

cat > auv_bringup/setup.py << PYEOF2
import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'auv_bringup'

setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob(os.path.join('launch', '*.py'))),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Your Name',
    maintainer_email='you@example.com',
    description="Top-level launch files and global parameters for starting the vehicle's software.",
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
        ],
    },
)
PYEOF2

cat > auv_bringup/setup.cfg << CFGEOF2
[develop]
script_dir=\$base/lib/auv_bringup
[install]
install_scripts=\$base/lib/auv_bringup
CFGEOF2

cat > auv_bringup/launch/bringup.launch.py << BRINGUPEOF
"""Top-level launch file: brings up sensor drivers + state estimator.

Control, vision, and mission launches are added here once those
packages have real nodes (see docs/architecture-roadmap.md for build order).

NOTE: verify the driver launch filenames below against each driver's own
launch/ folder once built, e.g. `ros2 launch vectornav --show-args`,
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
            PathJoinSubstitution([FindPackageShare('vectornav'), 'launch', 'vectornav.launch.py'])
        ])
    )

    ping_sonar_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([FindPackageShare('ping_sonar_ros'), 'launch', 'ping_sonar.launch.py'])
        ])
    )

    zed_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([FindPackageShare('zed_wrapper'), 'launch', 'zed_camera.launch.py'])
        ]),
        launch_arguments={'camera_model': 'zedm'}.items()
    )

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
        zed_launch,
        localization_launch,
    ])
BRINGUPEOF

echo "Created real bringup launch file"

# ---------- auv_localization: real EKF config + launch ----------
mkdir -p auv_localization/auv_localization auv_localization/resource auv_localization/launch auv_localization/config
touch auv_localization/auv_localization/__init__.py
touch auv_localization/resource/auv_localization

cat > auv_localization/setup.py << PYEOF3
import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'auv_localization'

setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob(os.path.join('launch', '*.py'))),
        (os.path.join('share', package_name, 'config'), glob(os.path.join('config', '*.yaml'))),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Your Name',
    maintainer_email='you@example.com',
    description="State estimation: fuses sensor data into one position/orientation/velocity estimate.",
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
        ],
    },
)
PYEOF3

cat > auv_localization/setup.cfg << CFGEOF3
[develop]
script_dir=\$base/lib/auv_localization
[install]
install_scripts=\$base/lib/auv_localization
CFGEOF3

cat > auv_localization/config/ekf.yaml << EKFYAMLEOF
# robot_localization EKF config.
# Fuses VN-100 orientation/angular velocity now.
# Depth (pose0) and DVL velocity (odom0) are wired in below but commented
# out until those sensors are actually connected -- see TODOs.

ekf_filter_node:
  ros__parameters:
    frequency: 30.0
    sensor_timeout: 0.1
    two_d_mode: false
    publish_tf: true
    map_frame: map
    odom_frame: odom
    base_link_frame: base_link
    world_frame: odom

    # VN-100: orientation (roll,pitch,yaw) + angular velocity (roll,pitch,yaw)
    imu0: /vectornav/imu
    imu0_config: [false, false, false,
                  true,  true,  true,
                  false, false, false,
                  true,  true,  true,
                  true,  true,  true]
    imu0_differential: false
    imu0_relative: false
    imu0_queue_size: 10
    imu0_remove_gravitational_acceleration: true

    # TODO (pressure sensor not wired yet): once it is, a depth_pose_node.py
    # in this package should convert its raw reading into this
    # PoseWithCovarianceStamped topic (z field only). Uncomment once that
    # node is publishing.
    # pose0: /localization/depth_pose
    # pose0_config: [false, false, true,
    #                false, false, false,
    #                false, false, false,
    #                false, false, false,
    #                false, false, false]
    # pose0_differential: false
    # pose0_relative: false
    # pose0_queue_size: 10

    # TODO (DVL not wired yet): surge/sway velocity once available
    # odom0: /dvl/odometry
    # odom0_config: [false, false, false,
    #                false, false, false,
    #                true,  true,  false,
    #                false, false, false,
    #                false, false, false]

    # Starting values -- tune against real sensor noise once on hardware.
    process_noise_covariance: [0.05, 0,    0,    0,    0,    0,    0,     0,     0,    0,    0,    0,    0,    0,    0,
                                0,    0.05, 0,    0,    0,    0,    0,     0,     0,    0,    0,    0,    0,    0,    0,
                                0,    0,    0.06, 0,    0,    0,    0,     0,     0,    0,    0,    0,    0,    0,    0,
                                0,    0,    0,    0.03, 0,    0,    0,     0,     0,    0,    0,    0,    0,    0,    0,
                                0,    0,    0,    0,    0.03, 0,    0,     0,     0,    0,    0,    0,    0,    0,    0,
                                0,    0,    0,    0,    0,    0.06, 0,     0,     0,    0,    0,    0,    0,    0,    0,
                                0,    0,    0,    0,    0,    0,    0.025, 0,     0,    0,    0,    0,    0,    0,    0,
                                0,    0,    0,    0,    0,    0,    0,     0.025, 0,    0,    0,    0,    0,    0,    0,
                                0,    0,    0,    0,    0,    0,    0,     0,     0.04, 0,    0,    0,    0,    0,    0,
                                0,    0,    0,    0,    0,    0,    0,     0,     0,    0.01, 0,    0,    0,    0,    0,
                                0,    0,    0,    0,    0,    0,    0,     0,     0,    0,    0.01, 0,    0,    0,    0,
                                0,    0,    0,    0,    0,    0,    0,     0,     0,    0,    0,    0.02, 0,    0,    0,
                                0,    0,    0,    0,    0,    0,    0,     0,     0,    0,    0,    0,    0.01, 0,    0,
                                0,    0,    0,    0,    0,    0,    0,     0,     0,    0,    0,    0,    0,    0.01, 0,
                                0,    0,    0,    0,    0,    0,    0,     0,     0,    0,    0,    0,    0,    0,    0.015]
EKFYAMLEOF

cat > auv_localization/launch/ekf.launch.py << EKFLAUNCHEOF
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.substitutions import PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    ekf_config = PathJoinSubstitution([
        FindPackageShare('auv_localization'), 'config', 'ekf.yaml'
    ])

    ekf_node = Node(
        package='robot_localization',
        executable='ekf_node',
        name='ekf_filter_node',
        output='screen',
        parameters=[ekf_config],
        remappings=[('odometry/filtered', '/odometry/filtered')]
    )

    return LaunchDescription([ekf_node])
EKFLAUNCHEOF

echo "Created real localization config + launch file"
echo "All done."
