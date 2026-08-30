import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'vn100_driver'

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
    install_requires=['setuptools', 'pyserial'],
    zip_safe=True,
    maintainer='WIRED_AUV',
    maintainer_email='reaf-tamu@gmail.com',
    description='Minimal ASCII-mode VN-100 driver, publishes sensor_msgs/Imu directly from $VNYMR sentences.',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'vn100_ascii_node = vn100_driver.vn100_ascii_node:main',
        ],
    },
)
