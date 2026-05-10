# RBE594 Eye-Tracked Manipulator

This repository is a modified version of the ROBOTIS OpenMANIPULATOR ROS 2 Packages repository. The original link to that repository can be found below.
- [OpenMANIPULATOR Repository](https://github.com/robotis-git/open_manipulator)

All code for this project is meant to be ran inside the docker container modified in this repository. To set this up, along with other helpful tools, it is highly recommended to run the quick start guide of the OpenMANIPULATOR-X robot arm found below.

- [Quick-Start Guide](https://emanual.robotis.com/docs/en/platform/openmanipulator_x/quick_start_guide/#docker-environment)

Before entering the docker container, make sure the container is running. The container is started with the following command, which is to be ran in the RBE594-Eyetracked-Manipulator/simulation/open_manipulator/ directory of this repository.

```
./docker/container.sh start
```

To enter the docker container, open a terminal and enter the RBE594-Eyetracked-Manipulator/simulation/open_manipulator/ directory of this repository, then run the following command.

```
./docker/container.sh enter
```

This should now convert your terminal session into one being ran inside the docker script. The first time starting it will likely take a considerable amount of time as it downloads and configures all of the packages. Once inside the container, you will need to build the custom packages created in this repository. Do so using the following commands.


```
colcon build
source install/setup.bash
```

To run this project, first connect to the physical robot, overhead camera, and eye tracking camera. Then, in a new terminal in the container, run the following command to run the hardware bringup of the robot.

```
ros2 launch open_manipulator_bringup open_manipulator_x.launch.py
```

This should move the robot to the starting position. Next, start the overhead camera code, ensuring that the checkerboard is uncovered so the camera can use it for calibration and undistortion. The checkerboard can be covered and food items be placed afterwards. This code should be run in a new terminal inside the container.

```
ros2 run overhead_cam overhead_cam
```

If you recieve an error regarding camera indices or the wrong camera is being used for this, modify RBE594-Eyetracked-Manipulator/simulation/open_manipulator/overhead_cam/overhead_cam/overhead_cam.py on the line setting the video capture device, specifically changing the number to the correct index (if unknown can either check using a basic OpenCV script or by starting at 0 and incrementing until it works). If modified, you must rerun the build and source commands mentioned previously to process the change.

```
vc = cv.VideoCapture(5)
```

Once this is set up, run the eye tracking code, ensuring the desired camera being used for eye tracking is in a stable position and facing the eyes of the user. In testing, it was found that keeping the camera below the gaze (pointed up towards the user) provided more accurate tracking. Upon running this code, the user with be guided to gaze at several targets as calibration. It is important this is done accurately, and that the user does not significantly move their head, or the calibration results may be inaccurate.

```
ros2 run EyeTrax EyeTrax
```

Similar to the overhead camera, if you recieve an error regarding camera indices or the wrong camera is being used for this, modify RBE594-Eyetracked-Manipulator/simulation/open_manipulator/EyeTrax/EyeTrax/EyeTrax.py on the line setting the camera index (if unknown can either check using a basic OpenCV script or by starting at 0 and incrementing until it works). If modified, you must rerun the build and source commands mentioned previously to process the change.

```
camera=9
```

Once the hardware bringup, overhead camera, and eyetracking scripts are all running, start the main control loop which takes in all the data from the other scripts, runs inverse kinematics with path planning, and incorporates basic user input to perform the feeding task.

```
ros2 run eyetracking_controller eyetracking_control
```

At this point, the system should be adjusted so the overhead camera live feed is full screen on the display (if not already) and the terminal that was used to run the eyetracking_controller script should be selected so input can be given. The user should now gaze at the desired food item on their screen, which should have a red circle around it (if not, it was found that more lighting, contrast, and centrally located food items were easier to detect). The robot should now move the fork directly above the food item that was being selected by gaze. The user should now press the space bar (depending on the performance of the CPU and keyboard of the system, this may not be responsive and holding the spacebar for a second may be needed) indicating to the robot that it should proceed with the feeding task. It will now move downwards, securing the food item on the fork before moving to the feeding pose. At this point, the user should eat (or simply remove if testing) the food item, then pressing / holding the space bar to indicate this has been completed. After this, the robot will return to the home position until it is detected the user is gazing at another food item.
