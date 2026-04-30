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

import rclpy
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

        self.overhead_cam_image_dims_subscription = self.create_subscription(
            Point, '/overhead_cam_image_dims', self.overhead_cam_image_dims_callback, 10
        )

        self.arm_joint_positions = [0.0] * 4
        self.arm_joint_names = ['joint1', 'joint2', 'joint3', 'joint4']

        self.linkLens = [0.128, 0.124, 0.126]
        self.linkOffs = [0.096326, 0.024]
        self.forkDims = [0.095, 0.045]

        self.jointLimits=((-np.pi, np.pi), (-1.5, 1.5), (-1.5, 1.4), (-1.7, 1.97))

        # self.arm_ee_positions = [0.274, 0, 0.205, 0]
        self.arm_ee_positions = [0.075, 0, 0.08, 0] # Starting position from bringup
        self.joints_home, success = self.IK(self.arm_ee_positions)
        if not success:
            self.get_logger().error('Failed to calculate IK for the home position.')
            self.joints_home = [0.0] * 4

        self.joint_received = False

        self.gaze_logging = True
        self.keypoins_logging = True
        self.img_dims_logging = True
        
        self.TLpixelsWindow = [0, 225] # top left of window in pixels
        self.BRpixelsWindow = [2559, 1376] # top right of window in pixels
        self.gazeXY = np.array([-1, -1])
        self.keypoints = []
        self.imageWidth = 0
        self.imageHeight = 0
        
        self.max_delta = 0.002
        self.last_command_time = time.time()
        self.command_interval = 0.02

        self.running = True  # for thread loop control

        self.get_logger().info('Waiting for /joint_states...')
        self.rate = self.create_rate(10)

    def overhead_cam_image_dims_callback(self, msg):
        # this is the coords from the message
        self.imageWidth = msg.x
        self.imageHeight = msg.y
        # self.get_logger().info(f'Received Image Dims: Width = {self.imageWidth}, Height = {self.imageHeight}')

    def eyetracking_state_callback(self, msg):
        # this is the coords from the message
        xCoord = msg.x
        yCoord = msg.y
        # self.get_logger().info(f'Received Gaze: X = {self.xCoord}, Y = {self.yCoord}')
        self.gazeXY = np.array([xCoord, yCoord])

    def keypoints_callback(self, msg):
        allKeypoints = msg.poses
        # self.get_logger().info(f'Received {len(allKeypoints)} keypoints!')
        
        # collects and prints all blob centroid keypoints
        # [self.get_logger().info(f'{[pt.position]}') for pt in allKeypoints]

        self.keypoints = [[pt.position.x, pt.position.y] for pt in allKeypoints]


    def process_data(self):
        TLpixel_meters = [0.0675, -0.1375] # Robot pose of TL camera pixel
        validImgDims = self.imageWidth > 0 and self.imageHeight > 0
        if validImgDims:
            if not self.img_dims_logging:
                self.img_dims_logging = True
        elif self.img_dims_logging:
            self.img_dims_logging = False
            self.get_logger().info('Waiting for image dimensions...')

        validGaze = self.TLpixelsWindow[0] < self.gazeXY[0] < self.BRpixelsWindow[0] and self.TLpixelsWindow[1] < self.gazeXY[1] < self.BRpixelsWindow[1]
        if validGaze:
            if not self.gaze_logging:
                self.gaze_logging = True
        elif self.gaze_logging:
            self.gaze_logging = False
            self.get_logger().info('Waiting for gaze...')

        if len(self.keypoints) > 0:
            if not self.keypoins_logging:
                self.keypoins_logging = True

            if validGaze and validImgDims:

                screenImageWidth = self.BRpixelsWindow[0] - self.TLpixelsWindow[0]
                imageScale = self.imageWidth / screenImageWidth

                adjustedGaze = (self.gazeXY - np.array(self.TLpixelsWindow)) * imageScale
                
                squareSize = 0.025 #meters
                numSquareX = 11
                totalXm = squareSize * numSquareX
                pixels2meters = totalXm / self.imageWidth
                # find closest keypoint to gaze point
                closestKeypoint = np.array(self.keypoints[0])
                shortestDist = np.linalg.norm(closestKeypoint - adjustedGaze)
                if len(self.keypoints) > 1:
                    for kpNum in range(1, len(self.keypoints)):
                        p = np.array(self.keypoints[kpNum])
                        dist = np.linalg.norm(p - adjustedGaze) # both must be numpy arrays for the subtraction to work

                        if dist <= shortestDist:
                            shortestDist = dist
                            closestKeypoint = p
                            
                print(f'Closest keypoint to gaze: {closestKeypoint} with distance {shortestDist}')
                x_meter_blob = closestKeypoint[0] * pixels2meters + TLpixel_meters[1]
                y_meter_blob = closestKeypoint[1] * pixels2meters + TLpixel_meters[0]

                blobCoords = [y_meter_blob, x_meter_blob]
                self.retrieve_food(blobCoords)
                self.return_home()

        elif self.keypoins_logging:
            self.keypoins_logging = False
            self.get_logger().info('Waiting for keypoints...')        
            
    
    def joint_state_callback(self, msg):
        if set(self.arm_joint_names).issubset(set(msg.name)):
            for i, joint in enumerate(self.arm_joint_names):
                index = msg.name.index(joint)
                self.arm_joint_positions[i] = msg.position[index]

        if 'rh_r1_joint' in msg.name:
            index = msg.name.index('rh_r1_joint')

        self.joint_received = True
        # self.get_logger().info(
        #     f'Received joint states: {self.arm_joint_positions}'
        # )

    def get_quintic_pos(self, q_start, q_end, t, T):
        q_start = np.array(q_start)
        q_end = np.array(q_end)
        
        s = 10 * (t/T)**3 - 15 * (t/T)**4 + 6 * (t/T)**5
        return q_start + (q_end - q_start) * s

    def retrieve_food(self, coords):
        Fv = self.forkDims[0] 
        Fh = self.forkDims[1]
        forkAng = -(np.pi/2 - np.arctan2(Fv, Fh))
        aboveBeforeFoodPose = [coords[0], coords[1], 0.1, forkAng]
        aboveBeforeFoodJoints, success = self.IK(aboveBeforeFoodPose)
                
        if not success:
            self.get_logger().error('Failed to calculate IK for the above food pose.')
            return
        
        atFoodPose = [coords[0], coords[1], 0.00, forkAng]
        atFoodJoints, success = self.IK(atFoodPose)

        if not success:
            self.get_logger().error('Failed to calculate IK for the at food pose.')
            return
        
        aboveAfterFoodPose = [coords[0], coords[1], 0.1, 0]
        aboveAfterFoodJoints, success = self.IK(aboveAfterFoodPose)

        if not success:
            self.get_logger().error('Failed to calculate IK for the above after food pose.')
            return
        
        desiredForkAng = np.pi/12
        angAdjusted = np.pi/2 - desiredForkAng
        eatingPose = [0.127, -0.3, 0.2, angAdjusted]
        eatingJoints, success = self.IK(eatingPose)

        if not success:
            self.get_logger().error('Failed to calculate IK for the eating pose.')
            return
        
        current_joints = self.arm_joint_positions 
        target_keyframes = [aboveBeforeFoodJoints, atFoodJoints, aboveAfterFoodJoints, eatingJoints]
        needConfirmAfterKeyframe = [1, 0, 0, 1]
        T = 2.5
        dt = 0.001
        
        start_pos = current_joints
        
        for point_num, goal_pos in enumerate(target_keyframes):
            t = 0.0
            while t < T:
                waypoint = self.get_quintic_pos(start_pos, goal_pos, t, T)
                
                self.arm_joint_positions = waypoint.tolist()
                self.send_arm_command()
                
                t += dt
                time.sleep(dt)
            start_pos = goal_pos
            if needConfirmAfterKeyframe[point_num]:
                self.get_logger().info('Waiting for confirmation before continuing. Press Space.')
                confirmed = False
                while not confirmed:
                    key = self.get_key()
                    if key == ' ':
                        confirmed = True
                    time.sleep(0.01)

    def return_home(self):
        current_joints = self.arm_joint_positions 
        
        T = 2.5
        dt = 0.001
        
        start_pos = current_joints
        goal_pos = self.joints_home
        
        t = 0.0
        while t < T:
            waypoint = self.get_quintic_pos(start_pos, goal_pos, t, T)
            
            self.arm_joint_positions = waypoint.tolist()
            self.send_arm_command()
            
            t += dt
            time.sleep(dt)

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
    
    def IK(self, pose):

        base_height = self.linkOffs[0]
        shoulder_h  = self.linkOffs[1]
        shoulder_v  = self.linkLens[0]
        L2          = self.linkLens[1]
        Fv = self.forkDims[0] 
        Fh = self.forkDims[1]

        x, y, z, phi = pose

        thetas = [0]*4

        thetas[0] = np.arctan2(y, x)
        r = np.sqrt(x**2 + y**2)

        Lf = np.sqrt(Fh**2 + Fv**2)
        delta = np.arctan2(Fv, Fh)
        phi_eff = phi - delta

        rw = r - Lf * np.cos(phi_eff)
        zw = z - base_height - Lf * np.sin(phi_eff)
        dw = np.sqrt(rw**2 + zw**2)

        shoulderLen = np.sqrt(shoulder_v**2 + shoulder_h**2)

        cbeta = (shoulderLen**2 + L2**2 - dw**2) / (2 * shoulderLen * L2)
        if abs(cbeta) > 1:
            print("Target is out of reach, no valid IK solution.")
            return [None] * 4, False
        
        sbeta = np.sqrt(1 - cbeta**2)

        beta = np.arctan2(sbeta, cbeta)
        
        psi = np.arctan2(shoulder_v, shoulder_h)

        thetas[2] = np.pi - psi - beta

        gamma = np.arcsin(L2 * np.sin(beta) / dw)
        tau = np.arcsin(shoulder_h / shoulderLen)

        alpha = np.arctan2(zw, rw)

        thetas[1] = np.pi/2 - tau - gamma - alpha

        thetas[3] = -thetas[1] - thetas[2] - phi

        for i in range(4):
            lo, hi = self.jointLimits[i]
            if not (lo <= thetas[i] <= hi):
                print(f"Joint {i+1} angle {thetas[i]:.2f} out of limits ({lo:.2f}, {hi:.2f})")
                return [None] * 4, False

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
            'Use 1/q, 2/w, 3/e, 4/r for +/- x, y, z, phi. Press ESC to exit.'
        )

        # TODO: either calculate algorithmically or add to readme, 
        # TL and BR are system dependent and may need to be adjusted.
        # self.TLpixelsWindow = [0, 225] # top left of overhead camera image on the laptop screen in pixels
        # self.BRpixelsWindow = [2559, 1376] # bottom right of overhead camera image on the laptop screen in pixels
        # self.imageHeight = 144 # height of overhead camera image in pixels
        # self.imageWidth = 320 # width of overhead camera image in pixels
        # self.gazeXY = np.array([1000, 1000]) # eyetracked gaze on the laptop screen in pixels
        # # self.keypoints = [[43, 43], [277, 43], [277, 103], [43, 103]] # keypoints in overhead camera image in pixels
        # self.keypoints = [[0,0], [0, 140], [319, 143], [319, 0]]
        while True:
            self.process_data()
            self.return_home()
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

                    self.arm_joint_positions, success = self.IK(self.arm_ee_positions)
                    self.get_logger().info(
                        f'Received coordinates! X: {self.arm_ee_positions[0]}, Y: {self.arm_ee_positions[1]}, Z: {self.arm_ee_positions[2]}, Phi: {self.arm_ee_positions[3]}'
                    )
                    if success:
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
