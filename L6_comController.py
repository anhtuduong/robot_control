# -*- coding: utf-8 -*-
"""
Created on Fri Nov  2 16:52:08 2018

@author: rorsolino
"""

#!/usr/bin/env python

#inherit from base controller
from base_controller.base_controller import BaseController
import rospy as ros 
import numpy as np
from numpy import nan
import copy

# L5 Controller specific
from base_controller.utils.controlRoutines import projectionBasedController, QPController
from base_controller.utils.common_functions import plotCoM, plotGRFs, plotConstraitViolation, plotJoint
from scipy.linalg import block_diag
from base_controller.utils.math_tools import motionVectorTransform

# L5 config file
import ex_6_conf as conf
robot_name = "hyq"

class Params:
    pass 
class ActualState:
    pass 
class DesiredState:
    pass 

class AdvancedController(BaseController): 

    def __init__(self):  
        BaseController.__init__(self)
        
        #send data to param server
        self.verbose = conf.verbose                                                                                                          
        self.u.putIntoGlobalParamServer("verbose", self.verbose)	
        
    def initVars(self):
        BaseController.initVars(self)
								
        p.des_basePoseW_log = np.empty((6,0 ))*nan
        p.des_baseTwistW_log = np.empty((6,0 ))*nan
        p.des_baseAccW_log = np.empty((6,0 )) *nan
        p.constr_viol = np.empty((4,0 )) *nan
        
        p.des_forcesW_log = np.empty((12,0 ))  *nan       
        p.Wffwd_log = np.empty((6,0 ))  *nan                    
        p.Wfbk_log = np.empty((6,0))  *nan  
        p.Wg_log = np.empty((6,0 ))  *nan                        
        p.constr_viol_log = np.empty((4,0 ))*nan
								
        p.two_pi_f             = 2*np.pi*conf.freq   # 2 PI * frequency  
        p.two_pi_f_amp         = np.multiply(p.two_pi_f, conf.amp) # A * 2 PI * frequency  
        p.two_pi_f_squared_amp = np.multiply(p.two_pi_f, p.two_pi_f_amp)  # A * (2 PI * frequency)^2

    def logData(self):
        BaseController.logData(self)
								
        p.des_basePoseW_log = np.hstack((p.des_basePoseW_log , p.des_pose.reshape(6,-1)))
        p.des_baseTwistW_log = np.hstack((p.des_baseTwistW_log , p.des_twist.reshape(6,-1)))
        p.des_baseAccW_log = np.hstack((p.des_baseAccW_log , p.des_acc.reshape(6,-1)))                    
        p.des_forcesW_log = np.hstack((p.des_forcesW_log , p.des_forcesW.reshape(12,-1)))
        p.Wffwd_log = np.hstack((p.Wffwd_log , p.Wffwd.reshape(6,-1)))               
        p.Wfbk_log =  np.hstack((p.Wfbk_log , p.Wfbk.reshape(6,-1)))          
        p.Wg_log =  np.hstack((p.Wg_log , p.Wg.reshape(6,-1)))          
        p.constr_viol_log = np.hstack((p.constr_viol_log, p.constr_viol.reshape(4,-1)))      

def talker(p):
    
    p.start()
    p.register_node()
    p.initVars()          
    p.startupProcedure(robot_name) 
    rate = ros.Rate(1/conf.dt) # 10hz
    
                                
    # Reset reference to actual value  
    p.x0 = copy.deepcopy(p.basePoseW)
    p.des_pose  = p.x0
    p.des_twist = np.zeros(6)
    p.des_acc = np.zeros(6)       

    # Control loop               
    while (p.time  < conf.exp_duration) or conf.CONTINUOUS:
        #update the kinematics
        p.updateKinematics()
                                
        # EXERCISE 1: Sinusoidal Reference Generation
        # Reference Generation
        p.des_pose  = p.x0 +  conf.amp*np.sin(p.two_pi_f*p.time + conf.phi)
        p.des_twist  = p.two_pi_f_amp * np.cos(p.two_pi_f*p.time + conf.phi)
        p.des_acc = - p.two_pi_f_squared_amp * np.sin(p.two_pi_f*p.time + conf.phi)
        #use this to compute acceleration for a custom trajectory
        #des_acc = np.subtract(des_twist, p.des_twist_old)/p.Ts
        #p.des__twist_old = des_base_twist
 
        # EXERCISE 6: Check static stability, move CoM out of the polygon   
        p.des_pose[p.u.sp_crd["LY"]] +=0.0004
    
        # EXERCISE 8.a: Swift the Com on triangle of LF, RF, LH
#        p.des_pose[p.u.sp_crd["LX"]] = 0.1
#        p.des_pose[p.u.sp_crd["LY"]] = 0.1 
        # EXERCISE 8.b: Unload RH leg 
#        if p.time > 2.0:                            
#            p.stance_legs[p.u.leg_map["RH"]] = False       
   
        des_state = DesiredState()
        des_state.des_pose = p.des_pose
        des_state.des_twist = p.des_twist
        des_state.des_acc = p.des_acc        
        act_state = ActualState()              
        act_state.act_pose = p.basePoseW
        act_state.act_twist = p.baseTwistW   

        # offset of the com wrt base origin in WF 
        params = Params()  
        params.gravityComp = False                                                  
        params.W_base_to_com = p.u.linPart(p.comPoseW)   -   p.u.linPart(p.basePoseW) 
        params.robot = p.robot
        params.robotInertiaB = p.compositeRobotInertiaB
        
        #################################################################          
        # compute desired contact forces from the whole-body controller                      
        #################################################################
          
        
        # EXERCISE 2: Projection-based controller (base frame)        
#        params.isCoMControlled = False 
#        params.gravityComp = False
#        params.ffwdOn = False        
#        p.des_forcesW, p.Wffwd, p.Wfbk, p.Wg = projectionBasedController(conf, act_state, des_state, p.W_contacts, p.stance_legs, params)

        # EXERCISE 3: Add Gravity Compensation (base frame)        
#        params.isCoMControlled = False 
#        params.gravityComp = True
#        params.ffwdOn = False                                       
#        p.des_forcesW, p.Wffwd, p.Wfbk, p.Wg = projectionBasedController(conf, act_state, des_state, p.W_contacts, p.stance_legs, params)
#     
        # EXERCISE 4: Add FFwd Term (base frame) 
#        params.isCoMControlled = False 
#        params.gravityComp = True
#        params.ffwdOn = True        
#        p.des_forcesW, p.Wffwd, p.Wfbk, p.Wg = projectionBasedController(conf, act_state, des_state, p.W_contacts, p.stance_legs, params)
#                                
#        # EXERSISE 5: Projection-based controller (CoM)    
#        # map from base to com frame (they are aligned)
#        act_state.act_pose = p.comPoseW
#        act_state.act_twist = p.comTwistW 
#        params.isCoMControlled = True 
#        params.robotInertiaB = p.centroidalInertiaB
#        params.gravityComp = True
#        params.ffwdOn = True 
#        p.des_forcesW, p.Wffwd, p.Wfbk, p.Wg = projectionBasedController(conf, act_state, des_state, p.W_contacts, p.stance_legs, params)
#        
       # EXERCISE 7: quasi-static QP controller (base frame) - unilateral constraints                
        normals = [None]*4                 
        normals[p.u.leg_map["LF"]] = np.array([0.0,0.0,1.0])
        normals[p.u.leg_map["RF"]] = np.array([0.0,0.0,1.0])
        normals[p.u.leg_map["LH"]] = np.array([0.0,0.0,1.0])
        normals[p.u.leg_map["RH"]] = np.array([0.0,0.0,1.0])    
        params.f_min = np.array([0.0,0.0,0.0, 0.0])    
        params.friction_coeff = np.array([0.6,0.6,0.6, 0.6])    
   
        params.isCoMControlled = False 
        params.gravityComp = True
        params.ffwdOn = True    
        params.frictionCones = False
        params.normals = normals
     
        p.des_forcesW, p.Wffwd, p.Wfbk, p.Wg, p.constr_viol =  QPController(conf, act_state, des_state, p.W_contacts, p.stance_legs, params)
        
        # EXERCISE 9: quasi-static QP controller (base frame) - friction cone constraints                                    
        #params.frictionCones = True       
        #p.des_forcesW, p.Wffwd, p.Wfbk, p.Wg, p.constr_viol =  QPController(conf, act_state, des_state, p.W_contacts, p.stance_legs, params)                                           
                                
        #################################################################          
        # map desired contact forces into torques (missing gravity compensation)                      
        #################################################################                                       
        p.jacsT = block_diag(np.transpose(p.wJ[p.u.leg_map["LF"]]), 
                        np.transpose(p.wJ[p.u.leg_map["RF"]] ), 
                        np.transpose(p.wJ[p.u.leg_map["LH"]] ), 
                        np.transpose(p.wJ[p.u.leg_map["RH"]]  ))
        p.tau_ffwd =   p.u.mapFromRos(p.h_joints) - p.jacsT.dot(p.des_forcesW)         
 
    
    
       # send desired command to the ros controller     
        p.send_des_jstate(p.q_des, p.qd_des, p.tau_ffwd)
        p.logData()    
        p.time = p.time + conf.dt 
        # plot actual (green) and desired (blue) contact forces 
        for leg in range(4):
            p.ros_pub.add_arrow(p.W_contacts[leg], p.u.getLegJointState(leg, p.grForcesW/400),"green")        
            p.ros_pub.add_arrow(p.W_contacts[leg], p.u.getLegJointState(leg, p.des_forcesW/400),"blue")        
        p.ros_pub.publishVisual()                        
                                
        #wait for synconization of the control loop
        rate.sleep()       
                # stops the while loop if  you prematurely hit CTRL+C                    
        if ros.is_shutdown():
            print ("Shutting Down")                    
            break;                                                
                             
    # restore PD when finished        
    p.pid.setPDs(400.0, 6.0, 0.0) 
    ros.sleep(1.0)                
    print ("Shutting Down")                 
    ros.signal_shutdown("killed")           
    p.deregister_node()        
    
    plotCoM('position', 0, p.time_log, p.des_basePoseW_log, p.basePoseW_log, p.des_baseTwistW_log, p.baseTwistW_log, p.des_baseAccW_log, p.Wffwd_log  + p.Wfbk_log + p.Wg_log             )
    #plotCoM('wrench', 1, p.time_log, p.des_basePoseW_log, p.basePoseW_log, p.des_baseTwistW_log, p.baseTwistW_log, p.des_baseAccW_log, p.Wffwd_log  + p.Wfbk_log + p.Wg_log             )
    #plotGRFs(2, p.time_log, p.des_forcesW_log, p.grForcesW_log)
    #plotConstraitViolation(3,p.constr_viol_log)            
    #plotJoint('torque',4, p.time_log, p.q_log, p.q_des_log, p.qd_log, p.qd_des_log, None, None, p.tau_log, p.tau_ffwd_log)
         
if __name__ == '__main__':
    p = AdvancedController()
    try:
        talker(p)
    except ros.ROSInterruptException:
        pass
    
        