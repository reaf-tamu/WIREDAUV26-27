from launch import LaunchDescription
from launch_ros.actions import Node
from launch.substitutions import PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    config = PathJoinSubstitution([
        FindPackageShare('auv_mission'), 'config', 'december_gate.yaml'
    ])
    return LaunchDescription([
        Node(
            package='auv_mission',
            executable='mission_node',
            name='mission_node',
            output='screen',
            parameters=[config],
        ),
    ])
