# Load used libraries
import numpy as np
import cv2 as cv
import glob
import math

# Function that performs camera calibration
# Inputs:
# boardX: integer being the number of corners in x
# boardY: integer being the number of corners in y
# calib_imgs_dir: string being the directory of where the calibration images are
# calib_results_dir: string being the directory of where the calibration results should be stored
# test_img_file: string being the name of the image file to undistort
def perform_calibration(boardX, boardY, calib_imgs_dir, calib_results_dir, test_img_file):
    # termination criteria
    criteria = (cv.TERM_CRITERIA_EPS + cv.TERM_CRITERIA_MAX_ITER, 30, 0.001)
    
    # prepare object points, like (0,0,0), (1,0,0), (2,0,0) ....,(6,5,0)
    objp = np.zeros((boardX*boardY,3), np.float32)
    objp[:,:2] = np.mgrid[0:boardX,0:boardY].T.reshape(-1,2)
    
    # Arrays to store object points and image points from all the images.
    objpoints = [] # 3d point in real world space
    imgpoints = [] # 2d points in image plane.
    
    # Loads all image file paths
    images = glob.glob(calib_imgs_dir + '*.jpg')
    print("image filepaths: "+ str(images))

    # Loops through all image file paths
    for fname in images:
        # Loads image
        img = cv.imread(fname)
        # Converts image to grayscale
        gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
    
        # Find the chess board corners
        ret, corners = cv.findChessboardCorners(gray, (boardX,boardY), None)

        # If found, add object points, image points (after refining them)
        if ret == True:
            # Appends object points to object points array
            objpoints.append(objp)
            # Finds corners
            corners2 = cv.cornerSubPix(gray,corners, (11,11), (-1,-1), criteria)
            # Appends corners to image points array
            imgpoints.append(corners2)
    
            # Draw and display the corners
            cv.drawChessboardCorners(img, (boardX,boardY), corners2, ret)
            cv.imshow('img', img)
            cv.waitKey(500)

    # Cleans up
    cv.destroyAllWindows()

    # Performs camera calibration
    ret, mtx, dist, rvecs, tvecs = cv.calibrateCamera(objpoints, imgpoints, gray.shape[::-1], None, None)

    # Prints and saves calibration matrix
    print("Calibration Matrix:", mtx)
    np.save(calib_results_dir+'calib_mat.npy', mtx)

    # Loads image to undistort
    test_img = cv.imread(calib_imgs_dir + test_img_file)
    # Gets image size
    h,  w = test_img.shape[:2]
    # Refines camera matrix and finds roi
    newcameramtx, roi = cv.getOptimalNewCameraMatrix(mtx, dist, (w,h), 1, (w,h))
    # Undistorts image
    dst = cv.undistort(test_img, mtx, dist, None, newcameramtx)
    # crop the image
    x, y, w, h = roi
    dst = dst[y:y+h, x:x+w]

    # Writes undistorted image to file
    cv.imwrite(calib_results_dir+'calibresult.png', dst)

    # Prints and saves refined camera matrix
    print("Refined Calibration Matrix:",newcameramtx)
    np.save(calib_results_dir+'calib_mat_refined.npy', newcameramtx)

    # Prints and saves distortion coefficients
    print("Distortion Coefficients:", dist)
    np.save(calib_results_dir+'dist_coeffs', dist)

    # Initializes mean error
    mean_error = 0
    # Loops through all object points
    for i in range(len(objpoints)):
        # Gets projection points
        imgpoints2, _ = cv.projectPoints(objpoints[i], rvecs[i], tvecs[i], mtx, dist)
        # Finds error by comparing the image points
        error = cv.norm(imgpoints[i], imgpoints2, cv.NORM_L2)/len(imgpoints2)
        # Adds error to mean
        mean_error += error
    # Divides mean error to actually get the mean instead of sum
    mean_error /= len(objpoints)

    # Prints and saves re-projection error
    print("Re-Projection Error", mean_error)
    np.save(calib_results_dir+'reproj_err', mean_error)

## Values
# interior Corners in x direction
boardX = 10
# interior Corners in y direction
boardY = 4
# Location of calibration images
calib_imgs_dir = '2.0_megapixel_cam_data/'
# Location of folder to save npy arrays
calib_results_dir = '2.0_megapixel_cam_results/'
# Name of test image file to undistort
test_img_file = '2026-04-01-184057.jpg'

# Running function to perform calibration, print/save metrics, and undistort image
perform_calibration(boardX, boardY, calib_imgs_dir, calib_results_dir, test_img_file)


def crop_checkerboard(img_file, boardX, boardY):
    img = cv.imread(img_file)
    
    # # The shape attribute returns a tuple in the order (height, width, channels)
    height, width, channels = img.shape
    # print(f"Width: {width}")
    # print(f"Height: {height}")

    cv.imshow('img', img)

    # use warpPerspective
    # get 4 source corners, and 4 destination corners

    # Find the chess board corners
    ret, corners = cv.findChessboardCorners(img, (boardX, boardY), None)

    top_left = corners[0][0]
    top_right = corners[boardX - 1][0]
    bottom_left = corners[-boardX][0]
    bottom_right = corners[-1][0]

    src = np.float32([
        top_left,
        top_right,
        bottom_right,
        bottom_left       
    ])
    print(src)
    print("src size:" + str(np.shape(src)))
    
    # destination corners are  based on longest side
    side1 = math.dist(top_left, top_right)
    side2 = math.dist(top_right, bottom_right)
    side3 = math.dist(bottom_right,bottom_left)
    side4 = math.dist(bottom_left,top_left) 

    sides = [side1, side2, side3, side4]
    long_side = max(sides)
    print(long_side)

    # assuming longest side is boardX corners and shortest is boardY
    short_side = long_side * (boardY/boardX)
    print(short_side)

    origin_x = 20.
    origin_y = 20.

    dst = np.float32([
        [origin_x, origin_y],
        [long_side,origin_y],
        [long_side,short_side],
        [origin_x,short_side]        
    ])
    print(dst)
    print("dst size:" + str(np.shape(dst)))

    # run warpPerspective
    M = cv.getPerspectiveTransform(src, dst)
    print(f'M =\n{M}')
    img_warped = cv.warpPerspective(img, M, (width, height), flags=cv.INTER_LINEAR)

    # display resulting image
    cv.imshow('img_warped', img_warped)
    cv.waitKey(10000)
    # input("press enter to exit")

    # crop image, easy now we know corners of board
    border_offset = 20 # offset from inner corners of checkerboard for cropping
    cropped = img_warped[0:int(short_side + border_offset), 0:int(long_side + border_offset)]

    cv.imshow('cropped', cropped)
    cv.waitKey(10000)



crop_checkerboard('2.0_megapixel_cam_results/calibresult.png', boardX, boardY)