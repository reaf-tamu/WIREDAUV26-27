from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='vn100_driver',
            executable='vn100_ascii_node',
            name='vn100_ascii_node',
            output='screen',
            parameters=[{
                'port': '/dev/vectornav',
                'baud': 115200,
                'frame_id': 'vectornav',
            }]
        )
    ])
