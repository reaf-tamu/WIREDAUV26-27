from launch import LaunchDescription
from launch_ros.actions import Node
from launch.substitutions import PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    config = PathJoinSubstitution([
        FindPackageShare('auv_control'), 'config', 'pid_gains.yaml'
    ])

    return LaunchDescription([
        Node(
            package='auv_control',
            executable='attitude_control_node',
            name='attitude_control_node',
            output='screen',
            parameters=[config]
        )
    ])
