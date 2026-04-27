# Load used libraries
import numpy as np
import cv2 as cv
import glob
import math

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseArray, Pose, Point
from builtin_interfaces.msg import Time
from std_msgs.msg import Header

def perform_calibration(boardX: int, boardY: int, calib_imgs_dir:str, calib_results_dir:str, test_img_file:str):
    # Function that performs camera calibration
    # Inputs:
    # boardX: integer being the number of corners in x
    # boardY: integer being the number of corners in y
    # calib_imgs_dir: string being the directory of where the calibration images are
    # calib_results_dir: string being the directory of where the calibration results should be stored
    # test_img_file: string being the name of the image file to undistort
    # Outputs:
    # dst: image matrix of corrected test_image
    
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
            cv.waitKey(50)

    # Cleans up
    cv.destroyAllWindows()

    # Performs camera calibration
    ret, mtx, dist, rvecs, tvecs = cv.calibrateCamera(objpoints, imgpoints, gray.shape[::-1], None, None)

    # Prints and saves calibration matrix
    print("Calibration Matrix:", mtx)
    np.save(calib_results_dir+'calib_mat.npy', mtx)

    # Loads image to undistort
    test_img = cv.imread(test_img_file)
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

    return dst


def flatten_image(img, mtx, dist): 
    # Inputs:
    # img - img matrix from camera, to be flattened - MatLike
    # mtx - calibration matrix, saved from initial calibration - MatLike
    # dist - dist matrix, saved from initial calibration - MatLike
    # Outputs:
    # flat - img matrix from camera, without distortion

    # Gets image size
    h,  w = img.shape[:2]
    # Refines camera matrix and finds roi
    newcameramtx, roi = cv.getOptimalNewCameraMatrix(mtx, dist, (w,h), 1, (w,h))
    # Undistorts image
    dst = cv.undistort(img, mtx, dist, None, newcameramtx)
    # crop the image
    x, y, w, h = roi
    flat = dst[y:y+h, x:x+w]

    return flat


def find_crop_vars(img, boardX: int, boardY: int, origin_xy: float):
    # returns cropped image
    # img - a corrected camera image (using calibration) (already imread'd)
    # boardX, boardY - # of intersections between squares in X and Y directions.

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
    # print(src)
    # print("src size:" + str(np.shape(src)))
    
    # destination corners are  based on longest side
    side1 = math.dist(top_left, top_right)
    side2 = math.dist(top_right, bottom_right)
    side3 = math.dist(bottom_right,bottom_left)
    side4 = math.dist(bottom_left,top_left) 

    sides = [side1, side2, side3, side4]
    long_side = max(sides)
    # print(long_side)

    # assuming longest side is boardX corners and shortest is boardY
    short_side = long_side * (boardY/boardX)
    # print(short_side)

    # origin_xy = 28.

    dst = np.float32([
        [origin_xy, origin_xy],
        [long_side,origin_xy],
        [long_side,short_side],
        [origin_xy,short_side]        
    ])
    # print(dst)
    # print("dst size:" + str(np.shape(dst)))

    # run warpPerspective
    M = cv.getPerspectiveTransform(src, dst)
    # print(f'M =\n{M}')

    return M, short_side, long_side


def crop_checkerboard(img, origin_xy: float, short_side:float, long_side:float, M):
    height, width, channels = img.shape
    img_warped = cv.warpPerspective(img, M, (width, height), flags=cv.INTER_LINEAR)

    # # display resulting image
    # cv.imshow('img_warped', img_warped)
    # cv.waitKey(0)
    # # input("press enter to exit")

    # crop image, easy now we know corners of board
    cropped = img_warped[0:int(short_side + origin_xy), 0:int(long_side + origin_xy)]

    return cropped


def detect_blobs_in_cropped(img, detector: cv.SimpleBlobDetector):

    # greyscale
    grey = cv.cvtColor(img, cv.COLOR_BGR2GRAY)

    # Otsu's thresholding after Gaussian filtering
    blur = cv.GaussianBlur(grey,(5,5),0)
    ret3,th3 = cv.threshold(blur,0,255,cv.THRESH_BINARY+cv.THRESH_OTSU)

    keypoints = detector.detect(th3)
    img_with_keypoints = cv.drawKeypoints(blur, keypoints, np.array([]), (0, 0, 255), cv.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)

    return img_with_keypoints


class OverheadCam(Node):
    def __init__(self):
        super().__init__('overhead_cam')
        self.keypoints_publisher = self.create_publisher(PoseArray, 'keypoints', 10)
        self.imageDims_publisher = self.create_publisher(Point, 'overhead_cam_image_dims', 10)

def main():
    '''this file can run on its own, and is designed to flatten and display the checkerboard workspace of the robot.'''

    ## INIT - things to run once at start

    ##  Values
    # interior Corners in x direction
    boardX = 10
    # interior Corners in y direction
    boardY = 4
    # Location of calibration images
    mother_dir = '/root/ros2_ws/src/open_manipulator/overhead_cam/overhead_cam/camera_calibration/2MPx_wide'
    # Location of folder to save npy arrays
    calib_results_dir = mother_dir + '_results/'

    # origin of chessboard coord frame, in px - needs tuning if camera changes
    origin_xy = 28.0 # TODO: Make it so this works by first getting the distance of the square (dist formula between consecutive corners) and then set the origin based off this as an offset

    # TODO: run calibration? test calibration?

    # make camera available
    vc = cv.VideoCapture(7)

    # Set resolution (Property 3 is Width, 4 is Height)
    vc.set(cv.CAP_PROP_FRAME_WIDTH, 640)
    vc.set(cv.CAP_PROP_FRAME_HEIGHT, 360)

    # simpleblobdetector
    params = cv.SimpleBlobDetector_Params()
    params.filterByArea = True
    params.minArea = 100
    params.filterByCircularity = False
    params.filterByConvexity = False
    params.filterByInertia = False

    detector = cv.SimpleBlobDetector_create(params)

    if vc.isOpened(): # try to get the first frame
        rval, frame = vc.read()
    else:
        rval = False

    M = short_side = long_side = None

    rclpy.init()

    oc = OverheadCam()

    ## LOOP - ros node go spin
    while rval:

        # perform all the functions on frame :D
        calibmtx = np.load(calib_results_dir + 'calib_mat.npy')
        dist = np.load(calib_results_dir + 'dist_coeffs.npy')
        camera = flatten_image(frame, calibmtx, dist)

        if short_side == None or long_side == None:
            M, short_side, long_side = find_crop_vars(camera, boardX, boardY, origin_xy)

        # crop the image
        cropped_camera = crop_checkerboard(camera, origin_xy, short_side, long_side, M)

        #greyscale the image
        grey = cv.cvtColor(cropped_camera, cv.COLOR_BGR2GRAY)

        # Otsu's thresholding after Gaussian filtering
        blur = cv.GaussianBlur(grey,(5,5),0)
        ret3,th3 = cv.threshold(blur,0,255,cv.THRESH_BINARY+cv.THRESH_OTSU)

        # run simpleblobdetector
        keypoints = detector.detect(th3)
        img_with_keypoints = cv.drawKeypoints(cropped_camera, keypoints, np.array([]), (0, 0, 255), cv.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)

        # publish keypoints as PoseArray
        keypoints_msg = PoseArray()
        header = Header()
        time = Time()
        time.sec = 0
        time.nanosec = 0
        header.stamp = time
        header.frame_id = "id"
        for keypoint in keypoints:
            pose = Pose()
            pose.position.x = keypoint.pt[0]
            pose.position.y = keypoint.pt[1]
            pose.position.z = 0.0
            pose.orientation.x = 0.0
            pose.orientation.y = 0.0
            pose.orientation.z = 0.0
            pose.orientation.w = 1.0
            keypoints_msg.poses.append(pose)
        oc.keypoints_publisher.publish(keypoints_msg)

        # publish image dimensions as Point
        imgHeight, imgWidth = cropped_camera.shape[:2]
        imageDims_msg = Point()
        imageDims_msg.x = float(imgWidth)
        imageDims_msg.y = float(imgHeight)
        imageDims_msg.z = float(0)
        oc.imageDims_publisher.publish(imageDims_msg)


        # do a bunch of stuff to fullscreen One image
        cv.namedWindow("Fullscreen Window", cv.WINDOW_NORMAL)
        cv.setWindowProperty("Fullscreen Window", cv.WND_PROP_FULLSCREEN, cv.WINDOW_FULLSCREEN)
        cv.imshow("Fullscreen Window", img_with_keypoints)
        

        rval, frame = vc.read()

        key = cv.waitKey(1)
        if key == 27: # exit on ESC
            break

    cv.destroyWindow("preview")
    vc.release()
    oc.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
    