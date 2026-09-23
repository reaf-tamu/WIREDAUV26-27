from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='auv_pressure',
            executable='pressure_node',
            name='pressure_node',
            output='screen',
            parameters=[{
                'i2c_bus': 1,
                'frame_id': 'pressure_sensor',
                'rate_hz': 10.0,
                'fluid_density_kg_m3': 997.0,
            }]
        )
    ])
