from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='auv_ping',
            executable='ping_node',
            name='ping_node',
            output='screen',
            parameters=[{
                'port': '/dev/ping1d',
                'baud': 115200,
                'frame_id': 'ping1d',
                'rate_hz': 10.0,
            }]
        )
    ])
