from launch import LaunchDescription
from launch_ros.actions import Node
from launch.substitutions import PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pid_gains_config = PathJoinSubstitution([
        FindPackageShare('auv_control'), 'config', 'pid_gains.yaml'
    ])

    pid_control_node = Node(
        package='auv_control',
        executable='pid_control_node',
        name='pid_control_node',
        output='screen',
        parameters=[pid_gains_config]
    )

    thruster_allocator_node = Node(
        package='auv_control',
        executable='thruster_allocator_node',
        name='thruster_allocator_node',
        output='screen',
    )

    thruster_interface_node = Node(
        package='auv_control',
        executable='thruster_interface_node',
        name='thruster_interface_node',
        output='screen',
    )

    return LaunchDescription([
        pid_control_node,
        thruster_allocator_node,
        thruster_interface_node,
    ])
