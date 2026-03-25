# currently pseudocode
# GOAL: have arm follow 2d eye tracking, hovering EE above the checkerboard

# import send_arm_command from open-manipulator-teleop/open_manipulator_teleop/open_manipulator_teleop/open_manipulator_x_teleop.py

import select
import sys
import termios
import threading
import time
import tty

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectory
from trajectory_msgs.msg import JointTrajectoryPoint


class SimpleGazeController(Node):
    
    def __init__(self):
        super().__init__('keyboard_controller') # maybe kill this, copied from keyboard teleop file

        # Publisher for arm joint control
        self.arm_publisher = self.create_publisher(
            JointTrajectory, '/arm_controller/joint_trajectory', 10
        )

        ## this would command the gripper, if we wanted that
        # self.gripper_client = ActionClient(
        #     self, GripperCommand, '/gripper_controller/gripper_cmd'
        # )

        # Subscriber for joint states
        self.subscription = self.create_subscription(
            JointState, '/joint_states', self.joint_state_callback, 10
        )

        self.arm_joint_positions = [0.0] * 4 # this is initial joint position / 'home' position?
        self.arm_joint_names = ['joint1', 'joint2', 'joint3', 'joint4']

        self.gripper_position = 0.0
        self.gripper_max = 0.019
        self.gripper_min = -0.01

        self.joint_received = False

        self.max_delta = 0.02 # this is MAX TELEOP SPEED for joints
        self.gripper_delta = 0.002 #MAX TELEOP SPEED for gripper
        self.last_command_time = time.time()
        self.command_interval = 0.02

        self.running = True  # for thread loop control

        self.get_logger().info('Waiting for /joint_states...')
        self.rate = self.create_rate(10)
    
    def checkGaze():
        # detect gaze x,y coords on the screen
        pass
        return Xscreen, Yscreen

    def screenToBoard(Xscreen, Yscreen):
        # Xscreen -> int or float, screen X coord
        # Yscreen -> int or floar, screen Y coord

        # Xboard -> int or float, workspace X coord
        # Yboard -> int or float, workspace Y coord

        # convert screen coords to workspace XY coords
        pass
        return Xboard, Yboard

    def ik(Xee, Yee, Zee):
        # Xee, Yee, Zee -> int or float, desired end-effector coords in workspace frame

        # joint1, joint2, joint3, joint4 -> floats, joint positions required for desired EE coords 

        # inverse kinematics to calculate joint position from end effector XYZ
        pass
        return [joint1, joint2, joint3, joint4]

    def sendArmCommand(jointPositions):
        # jointPositions -> array of 4 joint positions

        # pulled from open-manipulator-teleop/open_manipulator_teleop/open_manipulator_teleop/open_manipulator_x_teleop.py
        # sets up the command and sends joint positions to the armcheckerboard
        pass

Z_ee = 5 #PLACEHOLDER VALUE - calculate something sensical here

X_scr, Y_scr = checkGaze()
X_ee, Y_ee = screenToBoard(X_scr, Y_scr)

jointPositions = ik(X_ee, Y_ee, Z_ee)

sendArmCommand(jointPositions)
