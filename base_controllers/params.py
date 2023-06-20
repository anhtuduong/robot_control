# -*- coding: utf-8 -*-
"""
Created on Fri Jun 02 2019

@author: Anh Tu Duong 
"""

import numpy as np

robot_params = {}

robot_params['ur5'] ={'dt': 0.001, 
                       'kp': np.array([300, 300, 300, 30, 30, 1]),
                       'kd':  np.array([20, 20, 20, 5, 5, 0.5]),
                       #'q_0':  np.array([ 0.3, -1.3, 1.0, -0.7, 0.7, 0.5]), #limits([0,pi],   [0, -pi], [-pi/2,pi/2],)
                       'q_0':  np.array([-0.3222, -0.7805, -2.48, -1.6347, -1.5715, -1.0017]), #limits([0,pi],   [0, -pi], [-pi/2,pi/2],)
                       'joint_names': ['shoulder_pan_joint', 'shoulder_lift_joint', 'elbow_joint', 'wrist_1_joint', 'wrist_2_joint', 'wrist_3_joint'],
                       'ee_frame': 'tool0',
                       'control_mode': 'point', # 'trajectory','point'
                       'real_robot': False,
                       'control_type': 'position', # 'position', 'torque'
                       'gripper_sim': True,
                    #    'spawn_x' : 0.5,
                    #    'spawn_y' : 0.35,
                    #    'spawn_z' : 1.75,
                       'spawn_x' : 0,
                       'spawn_y' : 0,
                       'spawn_z' : 0,
                       'buffer_size': 50000, # note the frames are all aligned with base for joints = 0
                     #   'q_guess_pick': np.array([-2.32, -1.41, -2.19, -1.17, -1.65, 0.74]),
                     #   'q_guess_middle': np.array([-0.94, -0.60, -2.54, -1.66, -1.53, -0.64]),
                     #   'q_guess_place': np.array([-0.20, -1.28, -2.33, -1.14, -1.48, -1.38]),
                       'q_guess_pick': np.array([-2.41, -1.24, -2.44, -1.05, -1.59, 0.84]),
                       'q_guess_middle': np.array([0.55, -2.07, 2.31, 1.32, 4.72, -2.17]),
                       'q_guess_place': np.array([-0.23, -1.42, -2.47, -0.83, -1.59, -1.36]),
                       'bridge_trajectory': [np.array([-1.31, -1.37, -2.26, -1.07, -1.58, -0.25]),
                                             np.array([-1.75, -1.56, -2.08, -1.05, -1.58, 0.17]),
                                             np.array([-1.94, -0.96, -2.48, -1.24, -1.57, 0.37])],

                     }

verbose = False
plotting = True


