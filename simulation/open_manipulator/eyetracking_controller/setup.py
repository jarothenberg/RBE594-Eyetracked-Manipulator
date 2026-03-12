from glob import glob
#import os

from setuptools import find_packages
from setuptools import setup

package_name = 'eyetracking_controller'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=[]),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        #(os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='you',
    maintainer_email='you@email.com',
    description='Eyetracking and Keyboard controller for OpenManipulator-X',
    license='Apache License 2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'eyetracking_control = eyetracking_controller.eyetracking_control:main',
        ],
    },
)
