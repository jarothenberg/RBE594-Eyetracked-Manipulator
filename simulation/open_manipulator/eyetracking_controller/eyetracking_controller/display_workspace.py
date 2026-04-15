# Load used libraries
import numpy as np
import cv2 as cv
import glob
import math

from camera_calibration.calibration import *


'''this file can run on its own, and is designed to flatten and display the checkerboard workspace of the robot.'''

## INIT - things to run once at start

# Values
# interior Corners in x direction
boardX = 10
# interior Corners in y direction
boardY = 4
# Location of calibration images
mother_dir = 'camera_calibration/2MPx_wide'
calib_imgs_dir = mother_dir + '_data/'
# Location of folder to save npy arrays
calib_results_dir = mother_dir + '_results/'

# origin of chessboard coord frame, in px - needs tuning if camera changes
origin_xy = 28.0

ROSE = (255, 29, 141) 

lower = np.array([0, 0, 0])
upper = np.array([170, 200, 170])

# TODO: run calibration? test calibration?

# cv.namedWindow("preview")
vc = cv.VideoCapture(2)

# Set resolution (Property 3 is Width, 4 is Height)
vc.set(cv.CAP_PROP_FRAME_WIDTH, 640)
vc.set(cv.CAP_PROP_FRAME_HEIGHT, 360)

if vc.isOpened(): # try to get the first frame
    rval, frame = vc.read()
else:
    rval = False

# M, short_side, long_side = find_crop_vars(frame, boardX, boardY, origin_xy)
M = short_side = long_side = None

## LOOP - ros node go spin
while rval:

    # perform all the functions on frame :D
    calibmtx = np.load(calib_results_dir + 'calib_mat.npy')
    dist = np.load(calib_results_dir + 'dist_coeffs.npy')
    camera = flatten_image(frame, calibmtx, dist)

    if short_side == None or long_side == None:
        M, short_side, long_side = find_crop_vars(camera, boardX, boardY, origin_xy)

    cropped_camera = crop_checkerboard(camera, origin_xy, short_side, long_side, M)

    blur = cv.blur(cropped_camera, (4, 4))
    mask = cv.inRange(blur, lower, upper)

    # # do a bunch of stuff to fullscreen the image
    # cv.namedWindow("Fullscreen Window", cv.WINDOW_NORMAL)
    # cv.setWindowProperty("Fullscreen Window", cv.WND_PROP_FULLSCREEN, cv.WINDOW_FULLSCREEN)
    # cv.imshow("Fullscreen Window", mask)

    cv.imshow("src", cropped_camera)
    cv.imshow("mask", mask)

    rval, frame = vc.read()

    key = cv.waitKey(1)
    if key == 27: # exit on ESC
        break

cv.destroyWindow("preview")
vc.release()
