# Load used libraries
import numpy as np
import cv2 as cv
import glob
import math

from camera_calibration.calibration import *

def detect_blobs_in_cropped(img):

    # simpleblobdetector
    params = cv.SimpleBlobDetector_Params()
    params.filterByArea = True
    params.minArea = 100
    params.filterByCircularity = False
    params.filterByConvexity = False
    params.filterByInertia = False

    detector = cv.SimpleBlobDetector_create(params)

    # greyscale
    grey = cv.cvtColor(img, cv.COLOR_BGR2GRAY)

    # Otsu's thresholding after Gaussian filtering
    blur = cv.GaussianBlur(grey,(5,5),0)
    ret3,th3 = cv.threshold(blur,0,255,cv.THRESH_BINARY+cv.THRESH_OTSU)

    keypoints = detector.detect(th3)
    img_with_keypoints = cv.drawKeypoints(blur, keypoints, np.array([]), (0, 0, 255), cv.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)

    return img_with_keypoints

# contours, hierarchy = cv.findContours(edges, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE)
# allthethings = cv.drawContours(img_with_keypoints, contours, -1, (0, 255, 0), thickness=cv.FILLED) #---set the last parameter to -1

# # do a bunch of stuff to fullscreen the image
# cv.namedWindow("Fullscreen Window", cv.WINDOW_NORMAL)
# cv.setWindowProperty("Fullscreen Window", cv.WND_PROP_FULLSCREEN, cv.WINDOW_FULLSCREEN)
# cv.imshow("Fullscreen Window", allthethings)

# filepath of image to be blob-detected
fname = "image.png"

img = cv.imread(fname)

img_out = detect_blobs_in_cropped(img)

cv.imshow("blob detection", img_out)
cv.waitKey(0)