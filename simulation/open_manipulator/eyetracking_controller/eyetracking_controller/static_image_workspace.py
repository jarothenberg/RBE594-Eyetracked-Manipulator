# Load used libraries
import numpy as np
import cv2 as cv
import glob
import math

from camera_calibration.calibration import *

# simpleblobdetector
params = cv.SimpleBlobDetector_Params()
params.filterByArea = True
params.minArea = 100
params.filterByCircularity = False
params.filterByConvexity = False
params.filterByInertia = False

detector = cv.SimpleBlobDetector_create(params)

# filepath of imMatLikeage to be blob-detected
fname = "image.png"

img = cv.imread(fname)
img_out = detect_blobs_in_cropped(img, detector)

cv.imshow("blob detection", img_out)
cv.waitKey(0)

# TODO: add this fn to camera.calibration to keep everything in one place?MatLike