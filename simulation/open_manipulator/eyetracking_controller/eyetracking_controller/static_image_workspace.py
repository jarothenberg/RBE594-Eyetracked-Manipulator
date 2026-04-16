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

def detect_blobs_in_cropped(img, detector):

    # greyscale
    grey = cv.cvtColor(img, cv.COLOR_BGR2GRAY)

    # Otsu's thresholding after Gaussian filtering
    blur = cv.GaussianBlur(grey,(5,5),0)
    ret3,th3 = cv.threshold(blur,0,255,cv.THRESH_BINARY+cv.THRESH_OTSU)

    keypoints = detector.detect(th3)
    img_with_keypoints = cv.drawKeypoints(blur, keypoints, np.array([]), (0, 0, 255), cv.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)

    return img_with_keypoints

# filepath of image to be blob-detected
fname = "image.png"

img = cv.imread(fname)
img_out = detect_blobs_in_cropped(img, detector)

cv.imshow("blob detection", img_out)
cv.waitKey(0)

# TODO: add this fn to camera.calibration to keep everything in one place?