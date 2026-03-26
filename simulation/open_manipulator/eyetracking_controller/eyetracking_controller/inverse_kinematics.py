import numpy as np

def getIK(xe,ye,ze,phi, L1,L2,L3, L4):
    """
    Returns the joint angles that will cause the end-effector to be
    at the desired pose (x,y,z,phi) based on the inverse kinematics
    of the arm. If the pose is not possible, this method will throw
    an error.
    
    Args:
        pose (list or np.ndarray): The pose (x,y,z,phi) of the end-effector to
                                   calculate the corresponding joint angles for.
    
    Returns:
        np.ndarray: Array of valid joint angle solutions
    """
    # # Define Links and givens from pose
    # L1 = self.mDim[0]
    # L2 = self.mDim[1]
    # L3 = self.mDim[2]
    # L4 = self.mDim[3]

    # xe = pose[0]
    # ye = pose[1]
    # ze = pose[2]
    # phi = pose[3]  # pitch

    # thetas array with each row corresponding to one of the 
    # two possible solutions (elbow up vs down)
    thetas = np.zeros((4, 2))
    
    thetas[0, :] = [np.degrees(np.arctan2(ye, xe)), 
                    np.degrees(np.arctan2(ye, xe))]
    re = np.sqrt(xe**2 + ye**2)

    # Wrist position
    rw = re - L4 * np.cos(np.radians(phi))
    zw = ze - L1 - L4 * np.sin(np.radians(phi))
    dw = np.sqrt(rw**2 + zw**2)
    
    # Two values for Beta
    cbeta = (L2**2 + L3**2 - dw**2) / (2 * L2 * L3)
    
    # Check if the value is valid (should be between -1 and 1)
    if abs(cbeta) > 1:
        raise Exception("End-Effector Pose Unreachable")
    
    sbeta = [np.sqrt(1 - cbeta**2), -np.sqrt(1 - cbeta**2)]
    
    try:
        beta = [np.degrees(np.arctan2(sbeta[0], cbeta)), 
                np.degrees(np.arctan2(sbeta[1], cbeta))]
    except:
        raise Exception("End-Effector Pose Unreachable")
    
    # Constant value of psi
    psi = np.degrees(np.arctan2(128, 24))
    
    # 180 = psi + beta + theta3
    # Two values for theta3
    thetas[2, :] = 180 - psi - np.array(beta)
    
    # Two values for gamma, tau is a constant
    gamma = np.degrees(np.arcsin(L3 * np.sin(np.radians(beta)) / dw))
    tau = np.degrees(np.arcsin(24 * np.sin(np.radians(psi)) / 128))

    # One value for alpha
    alpha = np.degrees(np.arctan2(zw, rw))
    
    # 90 = alpha + gamma + tau + theta2
    # Two values for theta2
    thetas[1, :] = 90 - tau - gamma - alpha
    
    # phi = -theta2 - theta3 - theta4
    # Two values for theta4
    thetas[3, :] = -thetas[1, :] - thetas[2, :] - phi

    # Now check if each row in thetas is a valid solution based on
    # the physical joint limits:
    # Joint 1: (-180 180) (None)
    # Joint 2: (-115 115)
    # Joint 3: (-115 85)
    # Joint 4: (-100 120)
    limits = np.array([[-180, 180], 
                       [-120, 120], 
                       [-120, 90], 
                       [-105, 125]])

    q = []
    for i in range(2):
        valid = True
        for j in range(4):
            angle = thetas[j, i]
            if angle < limits[j, 0] or angle > limits[j, 1]:
                valid = False
                break
        if valid:
            q.append(thetas[:, i].copy())
    
    return np.array(q) if q else np.array([])

print(getIK(274, 0, 205, 0, 77, 130, 124, 126))