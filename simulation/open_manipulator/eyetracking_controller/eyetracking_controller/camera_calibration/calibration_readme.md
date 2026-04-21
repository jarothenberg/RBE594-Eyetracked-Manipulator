HOW TO CALIBRATE YOUR CAMERA

1. take 10-15 photos of the checkerboard of your choice, from different distances and angles, with your camera

2. put them in a folder in the camera_calibration directory

3. in the camera_calibration directory, make a folder to hold the calibration results, and a test uncalibration image

4. update parameters after line 103 of calibration.py
    a. update the # of interior corners (where 2 grid lines intersect) for both X and Y directions
    b. update filepaths to your data folder and your results folder
    c. choose any image file in your dataset, and put its name in as test_img_file

5. run the calibration.py script