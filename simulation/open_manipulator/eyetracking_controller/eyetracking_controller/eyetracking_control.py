#!/usr/bin/env python3
#
# Copyright 2024 ROBOTIS CO., LTD.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Author: Sungho Woo

import select
import sys
import termios
import threading
import time
import tty

from control_msgs.action import GripperCommand
import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectory
from trajectory_msgs.msg import JointTrajectoryPoint
import numpy as np
from geometry_msgs.msg import PoseArray, Point

class KeyboardController(Node):

    def __init__(self):
        super().__init__('keyboard_controller')

        # Publisher for arm joint control
        self.arm_publisher = self.create_publisher(
            JointTrajectory, '/arm_controller/joint_trajectory', 10
        )

        # Action client for GripperCommand
        self.gripper_client = ActionClient(
            self, GripperCommand, '/gripper_controller/gripper_cmd'
        )

        # Subscriber for joint states
        self.subscription = self.create_subscription(
            JointState, '/joint_states', self.joint_state_callback, 10
        )

        self.eyetracking_subscription = self.create_subscription(
            Point, '/eyetracking_pose', self.eyetracking_state_callback, 10
        )

        self.keypoints_subscription = self.create_subscription(
            PoseArray, '/keypoints', self.keypoints_callback, 10
        )

        self.arm_joint_positions = [0.0] * 4
        self.arm_joint_names = ['joint1', 'joint2', 'joint3', 'joint4']

        self.linkLens = [0.128, 0.124, 0.126]
        self.linkOffs = [0.077, 0.024] # Simulated Robot
        # self.linkOffs = [0.096326, 0.024] # Real Robot

        # self.arm_ee_positions = [0.274, 0, 0.205, 0]
        self.arm_ee_positions = [0.16, 0, 0.145, 0] # Starting position from bringup

        self.gripper_position = 0.0
        self.gripper_max = 0.019
        self.gripper_min = -0.01

        self.joint_received = False
        self.eyetracking_pose_recieved = False

        self.max_delta = 0.002
        self.gripper_delta = 0.002
        self.last_command_time = time.time()
        self.command_interval = 0.02

        self.running = True  # for thread loop control

        self.get_logger().info('Waiting for /joint_states...')
        self.rate = self.create_rate(10)

    def eyetracking_state_callback(self, msg):
        self.eyetracking_pose_recieved = True
        xCoord = msg.x
        yCoord = msg.y
        TL = [69, 167]
        BR = [1473, 1566]
        width = BR[0] - TL[0]
        height = BR[1] - TL[1]
        squareSize = 25 #mm
        numSquareX = 10
        numSquareY = 10
        totalYmm = squareSize * numSquareY
        totalYmm_pixel = totalYmm / height
        totalXmm = squareSize * numSquareX
        totalXmm_pixel = totalXmm / width
        if TL[0] <= xCoord <= BR[0] and TL[1] <= yCoord <= BR[1]:
            x_meter = ((xCoord - TL[0]) * totalXmm_pixel) / 1000
            y_meter = -((yCoord - TL[1] - height/2) * totalYmm_pixel)/1000

            self.arm_ee_positions = [x_meter, y_meter, 0.205, 0.0]
            self.arm_joint_positions, success = self.IK(self.arm_ee_positions)
            if success:
                self.get_logger().info(
                    f'Received coordinates! X: {x_meter}, Y: {y_meter}'
                )
                self.send_arm_command()

    def keypoints_callback(self, msg):
        allKeypoints = msg.poses
        self.get_logger().info(f'Received {len(allKeypoints)} keypoints!')
        [self.get_logger().info(f'{[pt.position]}') for pt in allKeypoints]

    def joint_state_callback(self, msg):
        if set(self.arm_joint_names).issubset(set(msg.name)):
            for i, joint in enumerate(self.arm_joint_names):
                index = msg.name.index(joint)
                self.arm_joint_positions[i] = msg.position[index]

        if 'rh_r1_joint' in msg.name:
            index = msg.name.index('rh_r1_joint')
            self.gripper_position = msg.position[index]

        self.joint_received = True
        # self.get_logger().info(
        #     f'Received joint states: {self.arm_joint_positions}, '
        #     f'Gripper: {self.gripper_position}'
        # )

    def get_key(self, timeout=0.01):
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)
            rlist, _, _ = select.select([sys.stdin], [], [], timeout)
            if rlist:
                return sys.stdin.read(1)
            return None
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    def send_arm_command(self):
        arm_msg = JointTrajectory()
        arm_msg.joint_names = self.arm_joint_names
        arm_point = JointTrajectoryPoint()
        arm_point.positions = self.arm_joint_positions
        arm_point.time_from_start.sec = 0
        arm_msg.points.append(arm_point)
        self.arm_publisher.publish(arm_msg)
        # self.get_logger().info(f'Arm command sent: {self.arm_joint_positions}')
        #TODO check if connected to hardware robot and send if connected

    def send_gripper_command(self):
        goal_msg = GripperCommand.Goal()
        goal_msg.command.position = self.gripper_position
        goal_msg.command.max_effort = 10.0

        # self.get_logger().info(f'Sending gripper command: {goal_msg.command.position}')
        self.gripper_client.wait_for_server()
        self.gripper_client.send_goal_async(goal_msg)
        #TODO check if connected to hardware robot and send if connected

    
    def IK(self, pose):

        x = pose[0]
        y = pose[1]
        z = pose[2]
        phi = pose[3]
        
        L1 = self.linkLens[0]
        L2 = self.linkLens[1]
        L3 = self.linkLens[2]

        O1 = self.linkOffs[0]
        O2 = self.linkOffs[1]

        thetas = [0]*4

        thetas[0] = np.arctan2(y, x)
        
        r = np.sqrt(x**2 + y**2) - O2
        z_adj = z - O1

        rw = r - L3 * np.cos(phi)
        zw = z_adj - L3 * np.sin(phi)

        D_origin = rw**2 + zw**2
        cos_t2 = (D_origin - L1**2 - L2**2) / (2 * L1 * L2)

        if abs(cos_t2) > 1:
            print("OUT OF RANGE")
            return [None]*4, False

        thetas[2] = np.arccos(cos_t2) - (np.pi / 2)
        thetas[1] = np.arctan2(rw, zw) - np.arctan2(L2 * np.cos(thetas[2]), L1 - L2 * np.sin(thetas[2]))
        thetas[3] = -phi - thetas[2] - thetas[1]

        limits = [
            (-np.pi, np.pi),
            (-1.5, 1.5),
            (-1.5, 1.4),
            (-1.7, 1.97)
        ]

        for i in range(4):
            thetas[i] = np.arctan2(np.sin(thetas[i]), np.cos(thetas[i]))
            
            low, high = limits[i]
            if not (low <= thetas[i] <= high):
                print(f"LIMIT VIOLATION: Joint {i+1} at {np.degrees(thetas[i]):.2f}° "
                    f"is outside [{np.degrees(low):.0f}°, {np.degrees(high):.0f}°]")
                return [None]*4, False
            
        return thetas, True


    # def closest_keypoint(pointin, keypoint_list):
    #     point = [pointin.x, pointin.y]
        
    #     shortestDist = sys.float_info.max
        
    #     for k in keypoint_list:
    #         p = [k.Point.x, k.Point.y]
            
    #         dist = np.linalg.norm(p - point)
            
    #         if dist < shortestDist:
    #             shortestDist = dist
    #         elif dist == shortestDist:
    #             pass #TODO: handle both at equal dist
            
    #     print("shortest distance: " + str(shortestDist))
    #     return shortestDist
    

    def run(self):
        while (not self.joint_received) and rclpy.ok() and self.running:
            self.get_logger().info('Waiting for initial joint states and eyetracking pose...')
            # rclpy.spin_once(self, timeout_sec=1.0)

        self.get_logger().info('Ready to receive keyboard and eyetracking input!')
        self.get_logger().info(
            'Use 1/q, 2/w, 3/e, 4/r for joints 1-4, o/p for gripper. Press ESC to exit.'
        )
        try:
            while rclpy.ok() and self.running:
                key = self.get_key()
                current_time = time.time()

                if key is None:
                    continue

                if current_time - self.last_command_time >= self.command_interval:
                    if key == '\x1b':  # ESC
                        self.running = False
                        break
                    elif key == '1':
                        self.arm_ee_positions[0] += self.max_delta
                    elif key == 'q':
                        self.arm_ee_positions[0] -= self.max_delta
                    elif key == '2':
                        self.arm_ee_positions[1] += self.max_delta
                    elif key == 'w':
                        self.arm_ee_positions[1] -= self.max_delta
                    elif key == '3':
                        self.arm_ee_positions[2] += self.max_delta
                    elif key == 'e':
                        self.arm_ee_positions[2] -= self.max_delta
                    elif key == '4':
                        self.arm_ee_positions[3] += self.max_delta
                    elif key == 'r':
                        self.arm_ee_positions[3] -= self.max_delta
                    elif key == 'o':  # Open gripper
                        new_pos = min(
                            self.gripper_position + self.gripper_delta, self.gripper_max 
                        )
                        self.gripper_position = new_pos
                        self.send_gripper_command()
                    elif key == 'p':  # Close gripper
                        new_pos = max(
                            self.gripper_position - self.gripper_delta, self.gripper_min
                        )
                        self.gripper_position = new_pos
                        self.send_gripper_command()

                    self.arm_joint_positions, success = self.IK(self.arm_ee_positions)
                    if success:
                        self.get_logger().info(
                            f'Received coordinates! X: {self.arm_ee_positions[0]}, Y: {self.arm_ee_positions[1]}'
                        )
                        self.send_arm_command()
                        self.last_command_time = current_time

        except Exception as e:
            self.get_logger().error(f'Exception in run loop: {e}')


def main():
    rclpy.init()
    node = KeyboardController()
    thread = threading.Thread(target=node.run)
    thread.start()

    try:
        rclpy.spin(node)
        while thread.is_alive():
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass

    node.running = False
    thread.join()
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
