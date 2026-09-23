import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'auv_pressure'

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
    maintainer='WIRED_AUV',
    maintainer_email='reaf-tamu@gmail.com',
    description='Bar02 pressure/depth driver using the official ms5837-python library.',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'pressure_node = auv_pressure.pressure_node:main',
        ],
    },
)
