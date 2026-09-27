import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'auv_control'

setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'config'), glob(os.path.join('config', '*.yaml'))),
        (os.path.join('share', package_name, 'launch'), glob(os.path.join('launch', '*.py'))),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Your Name',
    maintainer_email='you@example.com',
    description="PID control loops and thruster allocation.",
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'pid_control_node = auv_control.pid_control_node:main',
            'thruster_allocator_node = auv_control.thruster_allocator_node:main',
            'thruster_interface_node = auv_control.thruster_interface_node:main',
            'publish_setpoint = auv_control.publish_setpoint:main',
        ],
    },
)
