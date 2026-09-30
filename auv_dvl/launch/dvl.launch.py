from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='auv_dvl',
            executable='dvl_node',
            name='dvl_node',
            output='screen',
            parameters=[{
                'port': '/dev/dvl',
                'baud': 115200,
                'frame_id': 'dvl',
            }]
        )
    ])
