import sys
if sys.prefix == '/usr':
    sys.real_prefix = sys.prefix
    sys.prefix = sys.exec_prefix = '/root/ros2_ws/src/open_manipulator/install/open_manipulator_teleop'
