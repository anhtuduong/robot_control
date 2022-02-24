# -*- coding: utf-8 -*-
"""
Created on Thu Apr  2 18:07:44 2020

@author: mfocchi
"""
import os
import psutil
#from pinocchio.visualize import GepettoVisualizer
from custom_robot_wrapper import RobotWrapper
import numpy as np
import matplotlib.pyplot as plt
import sys
from termcolor import colored
import rospkg
import rospy as ros
import rosnode
import roslaunch
import rosgraph
from roslaunch.parent import ROSLaunchParent
import copy

#from urdf_parser_py.urdf import URDF
#make plot interactive
plt.ion()
plt.close() 

lw_des=7
lw_act=4   
marker_size= 0   


class Twist:
    linear = np.empty((3))*np.nan
    angular = np.empty((3))*np.nan
    def set(self, value):
        self.linear = copy.deepcopy(value[:3])
        self.angular = copy.deepcopy(value[3:])

class Pose:
    position = np.empty((3))*np.nan
    orientation = np.empty((3))*np.nan
    def set(self, value):
        self.position = copy.deepcopy(value[:3])
        self.orientation = copy.deepcopy(value[3:])
            
    
class State:
    
    def __init__(self, desired = False):
        self.pose = Pose()
        self.twist = Twist()
        if (desired):
            self.accel = Twist()
            
    def set(self, value):
        self.pose.set(value.getPose())
        self.twist.set(value.getTwist())
            
    def getPose(self):
        return np.hstack([self.pose.position, self.pose.orientation]) 
            
    def getTwist(self):
        return np.hstack([self.twist.linear, self.twist.angular])
        
def checkRosMaster():
    if rosgraph.is_master_online():  # Checks the master uri and results boolean (True or False)
        print(colored('ROS MASTER is Online','red'))
    else:
        print(colored('ROS MASTER is NOT Online, Starting roscore!!','red'))
        parent = ROSLaunchParent("roscore", [], is_core=True)  # run_id can be any string
        parent.start()

def startNode(node_name):
    
    nodes = rosnode.get_node_names()
    if "/reference_generator" in nodes:
        print(colored("Re Starting ref generator","red"))
        os.system("rosnode kill /"+node_name)
    package = node_name
    executable = node_name
    name = node_name
    namespace = ''
    node = roslaunch.core.Node(package, executable, name, namespace, output="screen")
    launch = roslaunch.scriptapi.ROSLaunch()
    launch.start()
    process = launch.launch(node)


def getRobotModel(robot_name="hyq", generate_urdf = False, xacro_path = None):    

    
    if (generate_urdf):  
        try:       
            #old way
            if (xacro_path is None):
                xacro_path = rospkg.RosPack().get_path(robot_name+'_description')+ '/robots/'+robot_name+'.urdf.xacro'
            
            package = 'xacro'
            executable = 'xacro'
            name = 'xacro'
            namespace = '/'
            args = xacro_path+ ' --inorder -o '+os.environ['LOCOSIM_DIR']+'/robot_urdf/'+robot_name+'.urdf'
     
            try:
                flywheel = ros.get_param('/flywheel')
                args+=' flywheel:='+flywheel
            except:
                pass          
            
            os.system("rosrun xacro xacro "+args)  
            #os.system("rosparam get /robot_description > "+os.environ['LOCOSIM_DIR']+'/robot_urdf/'+robot_name+'.urdf')  
            print ("URDF generated")
        except:
            print (robot_name+'_description not present')
            
        
    
    # Import the model
    ERROR_MSG = 'You should set the environment variable LOCOSIM_DIR"\n';
    path      = os.environ.get('LOCOSIM_DIR', ERROR_MSG)
    urdf      = path + "/robot_urdf/" + robot_name+ ".urdf"
    srdf      = path + "/robot_urdf/" + robot_name + ".srdf"
    robot = RobotWrapper.BuildFromURDF(urdf, [path,srdf ])
                                     
    #get urdf from ros just in case you need
    #robot_urdf_ros = URDF.from_parameter_server()                                                                                                                                                                                                                                                                                                              
    
    return robot                    

def plotJoint(name, figure_id, time_log, q_log, q_des_log, qd_log, qd_des_log, qdd_log, qdd_des_log, tau_log, tau_ffwd_log = None, joint_names = None):
    if name == 'position':
        plot_var_log = q_log
        if   (q_des_log is not None):
            plot_var_des_log = q_des_log
    elif name == 'velocity':
        plot_var_log = qd_log
        if   (qd_des_log is not None):
            plot_var_des_log  = qd_des_log
    elif name == 'acceleration':
        plot_var_log = qdd_log
        if   (qdd_des_log is not None):
            plot_var_des_log  = qdd_des_log
    elif name == 'torque':
        plot_var_log = tau_log
        if   (tau_ffwd_log is not None):                                    
            plot_var_des_log  = tau_ffwd_log 
        else:
          plot_var_des_log = None                                                
    else:
       print(colored("plotJopnt error: wrong input string", "red") )
       return                                   

    

    njoints = min(plot_var_log.shape)                                                                

    #neet to transpose the matrix other wise it cannot be plot with numpy array    
    fig = plt.figure(figure_id)                
    fig.suptitle(name, fontsize=20) 
    if joint_names is None:            
        labels_ur = ["1 - Shoulder Pan", "2 - Shoulder Lift","3 - Elbow","4 - Wrist 1","5 - Wrist 2","6 - Wrist 3"]
    else:
        labels_ur =joint_names
    labels_hyq = ["LF_HAA", "LF_HFE","LF_KFE","RF_HAA", "RF_HFE","RF_KFE","LH_HAA", "LH_HFE","LH_KFE","RH_HAA", "RH_HFE","RH_KFE"]
    labels_flywheel = ["LF_HAA", "LF_HFE","LF_KFE","RF_HAA", "RF_HFE","RF_KFE","LH_HAA", "LH_HFE","LH_KFE","RH_HAA", "RH_HFE","RH_KFE", 
                  "back_wheel", "front_wheel", "left_wheel", "right_wheel"]

    if njoints <= 6:
        labels = labels_ur         
    if njoints == 12:
        labels = labels_hyq                  
    if njoints == 16:
        labels = labels_flywheel
        
    for jidx in range(njoints):
     
        plt.subplot(njoints/2,2,jidx+1)
        plt.ylabel(labels[jidx])    
        if   (plot_var_des_log is not None):
             plt.plot(time_log, plot_var_des_log[jidx,:], linestyle='-', marker="o",markersize=marker_size, lw=lw_des,color = 'red')
        plt.plot(time_log, plot_var_log[jidx,:],linestyle='-',marker="o",markersize=marker_size, lw=lw_act,color = 'blue')
        
        plt.grid()
                
    

                
def plotEndeff(name, figure_id, time_log, x_log, x_des_log=None, xd_log=None, xd_des_log=None, euler = None, euler_des = None, f_log=None):
    plot_var_des_log = None
            
    if name == 'position':
        plot_var_log = x_log
        if   (x_des_log is not None):                                
           plot_var_des_log = x_des_log                            
    elif name == 'force':
        plot_var_log = f_log
    elif  name == 'velocity':                
        plot_var_log = xd_log
        if   (xd_des_log is not None):                                
             plot_var_des_log = xd_des_log         
    elif  name == 'orientation':    
        plot_var_log = euler                             
        plot_var_des_log = euler_des                               
    else:
       print("wrong choice")                    
                

                    
    fig = plt.figure(figure_id)
    fig.suptitle(name, fontsize=20)                   
    plt.subplot(3,1,1)
    plt.ylabel("end-effector x")
    if   (plot_var_des_log is not None):
         plt.plot(time_log, plot_var_des_log[0,:], lw=lw_des, color = 'red')                    
    plt.plot(time_log, plot_var_log[0,:], lw=lw_act, color = 'blue')
    plt.grid()
    
    plt.subplot(3,1,2)
    plt.ylabel("end-effector y")    
    if   (plot_var_des_log is not None):
         plt.plot(time_log, plot_var_des_log[1,:], lw=lw_des, color = 'red')                    
    plt.plot(time_log, plot_var_log[1,:], lw=lw_act, color = 'blue')
    plt.grid()
    
    plt.subplot(3,1,3)
    plt.ylabel("end-effector z")    
    if   (plot_var_des_log is not None):
        plt.plot(time_log, plot_var_des_log[2,:], lw=lw_des, color = 'red')                                        
    plt.plot(time_log, plot_var_log[2,:], lw=lw_act, color = 'blue')
    plt.grid()
      
    
def plotCoM(name, figure_id, time_log, des_basePoseW, basePoseW, des_baseTwistW, baseTwistW, des_baseAccW, wrenchW):
    plot_var_des_log = None
    if name == 'position':
        plot_var_log = basePoseW
        if   (des_basePoseW is not None):
            plot_var_des_log = des_basePoseW
    elif name == 'velocity':
        plot_var_log = baseTwistW
        if   (des_baseTwistW is not None):
            plot_var_des_log  = des_baseTwistW
    elif name == 'acceleration':
        if   (des_baseAccW is not None):
            plot_var_des_log  = des_baseAccW    
    elif name == 'wrench':
        plot_var_des_log  = wrenchW                                    
    else:
       print("wrong choice")                                    

           
                
    #neet to transpose the matrix other wise it cannot be plot with numpy array    
    fig = plt.figure(figure_id)
    fig.suptitle(name, fontsize=20)             
    plt.subplot(3,2,1)
    plt.ylabel("CoM X")    
    plt.plot(time_log, plot_var_log[0,:],linestyle='-', marker="o",markersize=marker_size,lw=lw_act,color = 'blue')
    if   (plot_var_des_log is not None):                
        plt.plot(time_log, plot_var_des_log[0,:], linestyle='-',  marker="o",markersize=marker_size, lw=lw_des,color = 'red')
   
    plt.grid()
                
    plt.subplot(3,2,3)
    plt.ylabel("CoM Y")
    plt.plot(time_log, plot_var_log[1,:],linestyle='-',marker="o",markersize=marker_size, lw=lw_act, color = 'blue', label="q")
    if   (plot_var_des_log is not None):           
        plt.plot(time_log, plot_var_des_log[1,:], linestyle='-', lw=lw_des,color = 'red', label="q_des")
    plt.legend(bbox_to_anchor=(-0.01, 1.115, 1.01, 0.115), loc=3, mode="expand")
    plt.grid()
    
    plt.subplot(3,2,5)
    plt.ylabel("CoM Z")    
    plt.plot(time_log, plot_var_log[2,:],linestyle='-',marker="o",markersize=marker_size, lw=lw_act,color = 'blue')    
    if   (plot_var_des_log is not None):    
       plt.plot(time_log, plot_var_des_log[2,:],linestyle='-',lw=lw_des,color = 'red')
    plt.grid()    
    
    plt.subplot(3,2,2)
    plt.ylabel("Roll")   
    plt.plot(time_log, plot_var_log[3,:].T,linestyle='-',marker="o",markersize=marker_size, lw=lw_act,color = 'blue')
    if   (plot_var_des_log is not None):    
        plt.plot(time_log, plot_var_des_log[3,:],linestyle='-',lw=lw_des,color = 'red')
    plt.grid()
    
    plt.subplot(3,2,4)
    plt.ylabel("Pitch")   
    plt.plot(time_log, plot_var_log[4,:],linestyle='-',marker="o",markersize=marker_size, lw=lw_act,color = 'blue')    
    if   (plot_var_des_log is not None):        
        plt.plot(time_log, plot_var_des_log[4,:],linestyle='-',lw=lw_des,color = 'red')
    plt.grid()
    
    plt.subplot(3,2,6)
    plt.ylabel("Yaw")
    plt.plot(time_log, plot_var_log[5,:],linestyle='-',marker="o",markersize=marker_size, lw=lw_act,color = 'blue')
    if   (plot_var_des_log is not None):             
        plt.plot(time_log, plot_var_des_log[5,:],linestyle='-',lw=lw_des,color = 'red')
    plt.grid()
                
         
    
        
def plotGRFs(figure_id, time_log, des_forces, act_forces):
           

    # %% Input plots

    fig = plt.figure(figure_id)
    fig.suptitle("ground reaction forces", fontsize=20)  
    plt.subplot(6,2,1)
    plt.ylabel("$LF_x$", fontsize=10)
    plt.plot(time_log, des_forces[0,:],linestyle='-',lw=lw_des,color = 'red')
    plt.plot(time_log, act_forces[0,:],linestyle='-',lw=lw_act,color = 'blue')
    plt.grid()
    plt.ylim((-100,100))
                
    plt.subplot(6,2,3)
    plt.ylabel("$LF_y$", fontsize=10)
    plt.plot(time_log, des_forces[1,:],linestyle='-',lw=lw_des,color = 'red')
    plt.plot(time_log, act_forces[1,:],linestyle='-',lw=lw_act,color = 'blue')
    plt.grid()
    plt.ylim((-100,100))
                
    plt.subplot(6,2,5)
    plt.ylabel("$LF_z$", fontsize=10)
    plt.plot(time_log, des_forces[2,:],linestyle='-',lw=lw_des,color = 'red')
    plt.plot(time_log, act_forces[2,:],linestyle='-',lw=lw_act,color = 'blue')
    plt.grid()
    plt.ylim((0,450))

    #RF
    plt.subplot(6,2,2)
    plt.ylabel("$RF_x$", fontsize=plot_var_des_log10)
    plt.plot(time_log, des_forces[3,:],linestyle='-',lw=lw_des,color = 'red')
    plt.plot(time_log, act_forces[3,:],linestyle='-',lw=lw_act,color = 'blue')
    plt.grid()
    plt.ylim((-100,100))
                
    plt.subplot(6,2,4)
    plt.ylabel("$RF_y$", fontsize=10)
    plt.plot(time_log, des_forces[4,:],linestyle='-',lw=lw_des,color = 'red')
    plt.plot(time_log, act_forces[4,:],linestyle='-',lw=lw_act,color = 'blue')
    plt.grid()
    plt.ylim((-100,100))
                
    plt.subplot(6,2,6)
    plt.ylabel("$RF_z$", fontsize=10)
    plt.plot(time_log, des_forces[5,:],linestyle='-',lw=lw_des,color = 'red')
    plt.plot(time_log, act_forces[5,:],linestyle='-',lw=lw_act,color = 'blue')
    plt.grid()
    plt.ylim((0,450))
                
     #LH
    plt.subplot(6,2,7)
    plt.ylabel("$LH_x$", fontsize=10)
    plt.plot(time_log, des_forces[6,:],linestyle='-',lw=lw_des,color = 'red')
    plt.plot(time_log, act_forces[6,:],linestyle='-',lw=lw_act,color = 'blue')
    plt.grid()
    plt.ylim((-100,100))
                
    plt.subplot(6,2,9)
    plt.ylabel("$LH_y$", fontsize=10)
    plt.plot(time_log, des_forces[7,:],linestyle='-',lw=lw_des,color = 'red')
    plt.plot(time_log, act_forces[7,:],linestyle='-',lw=lw_act,color = 'blue')
    plt.grid()
    plt.ylim((-100,100))
                
                
    plt.subplot(6,2,11)
    plt.ylabel("$LH_z$", fontsize=10)
    plt.plot(time_log, des_forces[8,:],linestyle='-',lw=lw_des,color = 'red')
    plt.plot(time_log, act_forces[8,:],linestyle='-',lw=lw_act,color = 'blue')
    plt.grid()
    plt.ylim((0,450))
                
     #RH
    plt.subplot(6,2,8)
    plt.ylabel("$RH_x$", fontsize=10)
    plt.plot(time_log, des_forces[9,:],linestyle='-',lw=lw_des,color = 'red')
    plt.plot(time_log, act_forces[9,:],linestyle='-',lw=lw_act,color = 'blue')
    plt.grid()
    plt.ylim((-100,100))
                
    plt.subplot(6,2,10)
    plt.ylabel("$RH_y$", fontsize=10)
    plt.plot(time_log, des_forces[10,:],linestyle='-',lw=lw_des,color = 'red')
    plt.plot(time_log, act_forces[10,:],linestyle='-',lw=lw_act,color = 'blue')
    plt.grid()
    plt.ylim((-100,100))
                        
    plt.subplot(6,2,12)
    plt.ylabel("$RH_z$", fontsize=10)
    plt.plot(time_log, des_forces[11,:],linestyle='-',lw=lw_des,color = 'red')
    plt.plot(time_log, act_forces[11,:],linestyle='-',lw=lw_act,color = 'blue')
    plt.grid()
    plt.ylim((0,450))

def plotConstraitViolation(figure_id,constr_viol_log):
    fig = plt.figure(figure_id)            
    plt.plot(constr_viol_log[0,:],label="LF")
    plt.plot(constr_viol_log[1,:],label="RF")
    plt.plot(constr_viol_log[2,:],label="LH")
    plt.plot(constr_viol_log[3,:],label="RH")
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3, ncol=2, mode="expand", borderaxespad=0.)
    plt.ylabel("Constr violation", fontsize=10)
    plt.grid()                                                                     

def plotEndeffImpedance(name, figure_id, x_log, x_des_log, f_log):                  
    
    title=""    
    
    if name == 'position':
        title="Force vs Displacement" 
    elif name == 'velocity':
        title="Force vs Velocity" 
    elif name == 'acceleration':
        title="Force vs Acceleration"                           
    else:
        print("wrong choice in impedance plotting")
 
    lw_act=4  
    lw_des=7
                    
#    fig = plt.figure(figure_id)    
    fig, axs = plt.subplots(3, 3)
    fig.suptitle(title, fontsize=20)
    
    axs[0, 0].plot((x_log[0,:].T-x_des_log[0,:].T), f_log[0,:].T, lw=lw_act, color = 'blue')
    axs[0, 0].set_title('Fx vs X')
    axs[0, 0].grid()
    
    axs[0, 1].plot((x_log[1,:].T-x_des_log[1,:].T), f_log[0,:].T, lw=lw_act, color = 'blue')
    axs[0, 1].set_title('Fx vs Y')
    axs[0, 1].grid()
    
    axs[0, 2].plot((x_log[2,:].T-x_des_log[2,:].T), f_log[0,:].T, lw=lw_act, color = 'blue')
    axs[0, 2].set_title('Fx vs Z')
    axs[0, 2].grid()
    
    axs[1, 0].plot((x_log[0,:].T-x_des_log[0,:].T), f_log[1,:].T, lw=lw_act, color = 'blue')
    axs[1, 0].set_title('Fy vs X')
    axs[1, 0].grid()
    
    axs[1, 1].plot((x_log[1,:].T-x_des_log[1,:].T), f_log[1,:].T, lw=lw_act, color = 'blue')
    axs[1, 1].set_title('Fy vs Y')
    axs[1, 1].grid()
    
    axs[1, 2].plot((x_log[2,:].T-x_des_log[2,:].T), f_log[1,:].T, lw=lw_act, color = 'blue')
    axs[1, 2].set_title('Fy vs Z')
    axs[1, 2].grid()
    
    axs[2, 0].plot((x_log[0,:].T-x_des_log[0,:].T), f_log[2,:].T, lw=lw_act, color = 'blue')
    axs[2, 0].set_title('Fz vs X')
    axs[2, 0].grid()
    
    axs[2, 1].plot((x_log[1,:].T-x_des_log[1,:].T), f_log[2,:].T, lw=lw_act, color = 'blue')
    axs[2, 1].set_title('Fz vs Y')
    axs[2, 1].grid()
    
    axs[2, 2].plot((x_log[2,:].T-x_des_log[2,:].T), f_log[2,:].T, lw=lw_act, color = 'blue')
    axs[2, 2].set_title('Fz vs Z')
    axs[2, 2].grid()
    
def plotJointImpedance(name, q_log, q_des_log, tau_log):
    
    title=""
    
    if name == 'position':
        title="Torque vs Angular Displacement"      
    elif name == 'velocity':
        title="Torue vs Angular Velocity" 
    elif name == 'acceleration':
        title="Torque vs Angular Acceleration"                           
    else:
        print("wrong choice in impedance plotting")
 
    lw_act=4  
    lw_des=3

    #Number of joints
    njoints = q_log.shape[0]                                                            
    
    #neet to transpose the matrix other wise it cannot be plot with numpy array    
    fig = plt.figure()                
    fig.suptitle(name, fontsize=20)             
    labels_ur = ["1 - Shoulder Pan", "2 - Shoulder Lift","3 - Elbow","4 - Wrist 1","5 - Wrist 2","6 - Wrist 3"]
    labels_hyq = ["LF_HAA", "LF_HFE","LF_KFE","RF_HAA", "RF_HFE","RF_KFE","LH_HAA", "LH_HFE","LH_KFE","RH_HAA", "RH_HFE","RH_KFE"]

    if njoints == 6:
        labels = labels_ur         
    if njoints == 12:
        labels = labels_hyq                  
                
    
    for jidx in range(njoints):
                
        plt.subplot(njoints/2,2,jidx+1)
        plt.ylabel(labels[jidx])    
        plt.plot(q_log[jidx,:].T-q_des_log[jidx,:].T, tau_log[jidx,:].T, linestyle='-', lw=lw_des,color = 'blue')
        plt.grid()
        
