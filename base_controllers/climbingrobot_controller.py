# -*- coding: utf-8 -*-
"""
Created on Fri Nov  2 16:52:08 2018

@author: rorsolino
"""

from __future__ import print_function
import rospy as ros
from utils.math_tools import *
import pinocchio as pin
np.set_printoptions(threshold=np.inf, precision = 5, linewidth = 1000, suppress = True)
import matplotlib.pyplot as plt
from numpy import nan
from utils.common_functions import plotJoint, plotCoMLinear
from termcolor import colored
import os
from rospy import Time
import tf
from base_controller_fixed import BaseControllerFixed
from gazebo_msgs.srv import SetModelConfiguration
from gazebo_msgs.srv import SetModelConfigurationRequest
from std_srvs.srv    import Empty, EmptyRequest
import roslaunch
from geometry_msgs.msg import Wrench, Point
from gazebo_msgs.msg import ContactsState
import scipy.io.matlab as mio


import  params as conf
robotName = "climbingrobot"

class ClimbingrobotController(BaseControllerFixed):
    
    def __init__(self, robot_name="ur5"):
        super().__init__(robot_name=robot_name)
        self.EXTERNAL_FORCE = False
        self.LOAD_MATLAB_TRAJ = True
        self.rope_index = 2
        self.leg_index = np.array([7,8])
        self.base_passive_joints = np.array([3,4,5])
        self.anchor_passive_joints = np.array([0,1])
        self.mountain_thickness = 0.1
        print("Initialized climbingrobot controller---------------------------------------------------------------")

    def applyForce(self, Fx, Fy, Fz, interval):
        wrench = Wrench()
        wrench.force.x = Fx
        wrench.force.y = Fy
        wrench.force.z = Fz
        wrench.torque.x = 0.
        wrench.torque.y = 0.
        wrench.torque.z = 0.
        reference_frame = "world" # you can apply forces only in this frame because this service is buggy, it will ignore any other frame
        reference_point = Point(x = 0., y = 0., z = 0.)
        self.apply_body_wrench(body_name=self.robot_name+"::base_link", reference_frame=reference_frame, reference_point=reference_point, wrench=wrench, start_time=ros.Time(),  duration=ros.Duration(interval))

    def loadModelAndPublishers(self, xacro_path=None):
        super().loadModelAndPublishers()
        self.pause_physics_client = ros.ServiceProxy('/gazebo/pause_physics', Empty)
        self.unpause_physics_client = ros.ServiceProxy('/gazebo/unpause_physics', Empty)
        self.reset_joints = ros.ServiceProxy('/gazebo/set_model_configuration', SetModelConfiguration)
        self.broadcaster = tf.TransformBroadcaster()
        self.sub_contact= ros.Subscriber("/" + self.robot_name + "/foot_bumper", ContactsState,
                                             callback=self._receive_contact, queue_size=1, buff_size=2 ** 24,
                                             tcp_nodelay=True)

    def rot2phi_theta(self, R):
        # this rotation is obtrained rotating phi about Z and theta about -Y axis as in Luigis convention
        #
        # syms psi theta phi
        # Rsym_x = [	1   ,    0     	  ,  	  0,
        #                 0   ,    cos(psi) ,  -sin(psi),
        #                 0   ,    sin(psi) ,  cos(psi)];
        # Rsym_y =[cos(theta) ,	 0  ,   sin(theta),
        #           0       ,    1  ,   0,
        #           -sin(theta) 	,	 0  ,  cos(theta)];
        #
        # Rsym_z =[cos(phi), -sin(phi), 0,
        #           sin(phi), cos(phi), 0,
        #           0, 0, 1];
        # the transpose is equal to rotate of -theta about Y  which is the same as rotating theta about -Y
        #R = simplify(Rsym_z * Rsym_y')

        #[cos(phi) * cos(theta), -sin(phi), -cos(phi) * sin(theta)]
        #[cos(theta) * sin(phi), cos(phi), -sin(phi) * sin(theta)]
        #[sin(theta), 0, cos(theta)]
        # note, with the urdf we have R = Rsym_y'*Rsym_x which has R(1,0) null

        theta = math.atan2(R[2, 0],R[2,2])
        phi = math.atan2(-R[1, 2], -R[0, 2]) #-cos(phi) * sin(theta) , -sin(phi) * sin(theta)

        # returns  pitch = theta,  yaw = phi
        return theta, phi

    def updateKinematicsDynamics(self):
        # q is continuously updated
        self.robot.computeAllTerms(self.q, self.qd )
        # joint space inertia matrix                
        self.M = self.robot.mass(self.q )
        # bias terms                
        self.h = self.robot.nle(self.q  , self.qd )
        #gravity terms                
        self.g = self.robot.gravity(self.q )
        #compute ee position  in the world frame  
        frame_name = conf.robot_params[self.robot_name]['ee_frame']
        # this is expressed in a workdframe with the origin attached to the base frame origin
        self.anchor_pos = self.robot.framePlacement(self.q, self.robot.model.getFrameId('anchor')).translation
        self.base_pos = self.robot.framePlacement(self.q, self.robot.model.getFrameId('base_link')).translation
        self.w_R_b = self.robot.framePlacement(self.q, self.robot.model.getFrameId('base_link')).rotation

        self.x_ee =  self.robot.framePlacement(self.q, self.robot.model.getFrameId(frame_name)).translation

        # compute jacobian of the end effector in the world frame (take only the linear part and the actuated joints part)
        self.J = self.robot.frameJacobian(self.q , self.robot.model.getFrameId(frame_name), True, pin.ReferenceFrame.LOCAL_WORLD_ALIGNED)[:3,:]
        self.Jleg = self.J[:, self.leg_index]
        self.dJdq = self.robot.frameClassicAcceleration(self.q , self.qd , None,  self.robot.model.getFrameId(frame_name), False).linear

        w_R_wire = self.robot.framePlacement(self.q, self.robot.model.getFrameId('wire')).rotation
        self.theta, self.phi =  self.rot2phi_theta(w_R_wire)
        self.l = self.q[p.rope_index]
        self.ldot = self.qd[p.rope_index]

        # compute com variables accordint to a frame located at the foot
        robotComB = pin.centerOfMass(self.robot.model, self.robot.data, self.q)

        # from ground truth
        self.com = self.base_pos + robotComB

        self.broadcaster.sendTransform(np.array([conf.robot_params[self.robot_name]['spawn_x'] -self.mountain_thickness/2, conf.robot_params[self.robot_name]['spawn_y'], 0.0]), (0.0, 0.0, 0.0, 1.0), ros.Time.now(), '/wall', '/world')

    def _receive_contact(self, msg):
        grf = np.zeros(3)
        grf[0] = msg.states[0].wrenches[0].force.x
        grf[1] = msg.states[0].wrenches[0].force.y
        grf[2] = msg.states[0].wrenches[0].force.z
        self.contactForceW = self.robot.framePlacement(self.q,  self.robot.model.getFrameId("lower_link")).rotation.dot(grf)

    def initVars(self):
        super().initVars()
        self.qdd_des =  np.zeros(self.robot.na)
        self.base_accel = np.zeros(3)
        # init new logged vars here
        self.com_log =  np.empty((3, conf.robot_params[self.robot_name]['buffer_size'] ))*nan

        self.simp_model_state_log = np.empty((3, conf.robot_params[self.robot_name]['buffer_size'])) * nan
        self.ldot_log = np.empty((conf.robot_params[self.robot_name]['buffer_size']))*nan
        self.base_pos_log = np.empty((3, conf.robot_params[self.robot_name]['buffer_size'])) * nan

        self.q_des_q0 = conf.robot_params[self.robot_name]['q_0']
        self.time_jump_log = np.empty((conf.robot_params[self.robot_name]['buffer_size'])) * nan

    def logData(self):
            if (self.log_counter<conf.robot_params[self.robot_name]['buffer_size'] ):
                self.simp_model_state_log[:, self.log_counter] = np.array([self.theta, self.phi, self.l])
                self.ldot_log[self.log_counter] = self.ldot
                self.base_pos_log[:, self.log_counter] = self.base_pos
                self.time_jump_log[self.log_counter] = self.time - self.end_thrusting
                pass
            super().logData()

    def deregister_node(self):
        super().deregister_node()
        os.system(" rosnode kill -a")
        os.system(" rosnode kill /gzserver /gzclient")
        os.system(" pkill rosmaster")

    def resetBase(self):
        # create the message
        req_reset_joints = SetModelConfigurationRequest()
        req_reset_joints.model_name = self.robot_name
        req_reset_joints.urdf_param_name = 'robot_description'
        req_reset_joints.joint_names = self.joint_names

        req_reset_joints.joint_positions = conf.robot_params[self.robot_name]['q_0'].tolist()
        # recompute the theta angle to have the anchor attached to the wall
        req_reset_joints.joint_positions[0] = math.atan2( 0.38, conf.robot_params[self.robot_name]['q_0'][p.rope_index])

        # send request and get response (in this case none)
        self.reset_joints(req_reset_joints)


    def spawnMountain(self):
        package = 'gazebo_ros'
        executable = 'spawn_model'
        name = 'spawn_climb_wall'
        namespace = '/'
        args = '-urdf -param climb_wall -model mountain -x '+ str(conf.robot_params[self.robot_name]['spawn_x'] - self.mountain_thickness/2)+ ' -y '+ str(conf.robot_params[self.robot_name]['spawn_y'])
        node = roslaunch.core.Node(package, executable, name, namespace,args=args,output="screen")
        self.launch = roslaunch.scriptapi.ROSLaunch()
        self.launch.start()
        process = self.launch.launch(node)

    def startupProcedure(self):
        if not self.EXTERNAL_FORCE:
            p.resetBase()
            p.spawnMountain() # I cannot apply body wrench if I spawn the mountain

        super().startupProcedure()

    def plotStuff(self):
        print("PLOTTING")
        # plotCoMLinear('com position', 1, p.time_log, None, p.com_log)
        # plotCoMLinear('contact force', 2, p.time_log, None, p.contactForceW_log)

        # plotJoint('joint position', 0, p.time_log, p.q_log, p.q_des_log, None, None, None, None, None, None,
        #           joint_names=conf.robot_params[p.robot_name]['joint_names'])
        #plot3D('states', 1,  ['theta', 'phi', 'l'], p.time_log - p.startJump, p.simp_model_state_log)
        traj_gazebo= p.base_pos_log - p.anchor_pos.reshape(3, 1) # is in anchor frame
        time_gazebo = p.time_log - p.end_thrusting
        plot3D('basePos', 2,  ['X', 'Y', 'Z'], time_gazebo, traj_gazebo , p.matvars['solution'].time, p.matvars['solution'].p )
        mio.savemat('test_gazebo.mat', {'solution': p.matvars['solution'], 'T_th': p.matvars['T_th'], 'mu': p.matvars['mu'],
                                        'Fun_max':p.matvars['Fun_max'], 'Fr_max':p.matvars['Fr_max'], 'p0':p.matvars['p0'],'pf': p.matvars['pf'],
                                        'time_gazebo': time_gazebo, 'traj_gazebo': traj_gazebo})


        plt.show(block=True)

def talker(p):

    p.start()
    p.startSimulator("slow.world")
    #p.startSimulator()
    p.loadModelAndPublishers()
    p.startupProcedure()
    p.initVars()
    p.q_des = np.copy(p.q_des_q0)

    #loop frequency
    rate = ros.Rate(1/conf.robot_params[p.robot_name]['dt'])
    p.updateKinematicsDynamics()
    p.tau_ffwd[p.rope_index] = p.g[p.rope_index]  # compensate gravitu in the virtual joint to go exactly there
    p.send_des_jstate(p.q_des, p.qd_des, p.tau_ffwd)
    # jump parameters
    p.startJump = 1.5

    # p.targetPos = np.array([0, 5., -8.])
    # p.jumps = [{"Fun": 4.5578, "Fut": 458.8895, "K_rope": 0.1000, "Tf": 1.0560}]
    # # {"Fun": 115.9, "Fut": 73, "K_rope": 14.4, "Tf": 0.93}]
    # p.thrustDuration = 0.05

    #override with matlab stuff
    p.matvars = mio.loadmat('test_optim.mat', squeeze_me=True,struct_as_record=False)
    p.jumps = [{"Fun": p.matvars['solution'].Fun, "Fut": p.matvars['solution'].Fut, "K_rope": 0.0, "Tf": p.matvars['solution'].Tf -  p.matvars['T_th']}]
    p.targetPos = p.matvars['pf']
    p.thrustDuration  = p.matvars['T_th']

    p.orientTime = 2.0
    p.stateMachine = 'idle'
    p.jumpNumber  = 0
    p.numberOfJumps = len(p.jumps)
    p.end_thrusting = np.inf

    while True:

        # update the kinematics
        p.updateKinematicsDynamics()

        #multiple jumps state machine
        if ( p.stateMachine == 'idle') and (p.time >= p.startJump) and (p.jumpNumber<p.numberOfJumps):
            print(colored("-------------------------------", "blue"))
            p.l_0 = p.l
            if (p.EXTERNAL_FORCE):
                    p.resetBase()
                    print(colored("Start applying force", "red"))
                    p.applyForce( p.jumps[p.jumpNumber]["Fun"], p.jumps[p.jumpNumber]["Fut"], 0., p.thrustDuration)
                    p.stateMachine = 'thrusting'
                    p.pid.setPDjoint(p.rope_index, 0., 0., 0.)
                    p.end_thrusting = p.startJump + p.thrustDuration
                    print(colored("Start Thrusting with EXT FORCE", "blue"))
            else:
                p.end_thrusting = p.startJump + p.orientTime + p.thrustDuration
                p.q_des[7] = math.atan2(p.jumps[p.jumpNumber]["Fut"], p.jumps[p.jumpNumber]["Fun"])
                print(colored(f"Start orienting leg to  : {p.q_des[7]}", "blue"))
                p.stateMachine = 'orienting_leg'

        if (p.stateMachine == 'orienting_leg') and (p.time > (p.startJump + p.orientTime)):
            print(colored(f"Start trusting Jump number : {p.jumpNumber}" , "blue"))
            p.tau_ffwd = np.zeros(p.robot.na)
            p.tau_ffwd[p.rope_index] = p.g[p.rope_index]  # compensate gravitu in the virtual joint to go exactly there
            p.pid.setPDjoint(p.base_passive_joints, 0., 0., 0.)
            p.pid.setPDjoint(p.leg_index, 0., 0., 0.)
            print(colored(f"ZERO LEG AND ROPE PD", "red"))
            # p.b_Fu = np.array([8, 0.0, 0.0])
            # p.w_Fu = p.w_R_b.dot(p.b_Fu)
            p.b_Fu_xy = np.array([p.jumps[p.jumpNumber]["Fun"], p.jumps[p.jumpNumber]["Fut"]])
            p.stateMachine = 'thrusting'

        if (p.stateMachine == 'thrusting'):
            if (p.EXTERNAL_FORCE):
                p.ros_pub.add_arrow(p.base_pos, np.array([p.jumps[p.jumpNumber]["Fun"], p.jumps[p.jumpNumber]["Fut"], 0.]) / 100., "red", scale= 3.)
            else:
                p.w_Fu_xy = p.w_R_b[:2, :2].dot(p.b_Fu_xy)
                p.tau_ffwd[p.leg_index] = - p.Jleg[:2,:].T.dot(p.w_Fu_xy)
                #p.tau_ffwd[p.rope_index] = - p.jumps[p.jumpNumber]["K_rope"] * (p.l - p.l_0)
                p.ros_pub.add_arrow( p.x_ee, np.hstack((p.w_Fu_xy, 0))/ 10., "red")

            if (p.time > p.end_thrusting):
                print(colored("Stop Trhusting", "blue"))
                p.stateMachine = 'flying'
                print(colored(f"RESTORING LEG PD", "red"))
                p.pid.setPDjoint(p.rope_index, 0., 0., 0.)
                # reenable  the PDs of default values for landing and reset the torque on the leg
                p.pid.setPDjoint(p.base_passive_joints, conf.robot_params[p.robot_name]['kp'], conf.robot_params[p.robot_name]['kd'] ,  0.)
                p.pid.setPDjoint(p.leg_index, conf.robot_params[p.robot_name]['kp'], conf.robot_params[p.robot_name]['kd'],  0.)
                p.tau_ffwd[p.leg_index] = np.zeros(2)
                print(colored("Start Flying", "blue"))

        if (p.stateMachine == 'flying'):
            # keep extending rope
            if p.LOAD_MATLAB_TRAJ:
                try:
                    # get index
                    a_bool = p.matvars['solution'].time > (p.time - p.end_thrusting)
                    force_index = min([i for (i, val) in enumerate(a_bool) if val])
                except:
                    force_index = -1
                Fr = p.matvars['solution'].Fr[force_index]
            else:
                Fr = -p.jumps[p.jumpNumber]["K_rope"] * (p.l - p.l_0)
            p.tau_ffwd[p.rope_index] = Fr

            rope_direction =  (p.base_pos - p.anchor_pos)/np.linalg.norm(p.base_pos - p.anchor_pos)
            p.ros_pub.add_arrow( p.base_pos, rope_direction*Fr/100., "red", scale=2.5)
            if (p.EXTERNAL_FORCE):
                end_flying = p.startJump  + p.thrustDuration +  p.jumps[p.jumpNumber]["Tf"]
            else:
                end_flying = p.startJump + p.orientTime + p.thrustDuration + p.jumps[p.jumpNumber]["Tf"]

            if (p.time >= end_flying):
                print(colored("Stop Flying", "blue"))
                # reset the qdes
                p.stateMachine = 'idle'
                print(colored(f"RESTORING ROPE PD", "red"))
                # enable PD for rope and reset the PD reference to the new estension
                # sample the new elongation
                p.q_des[p.rope_index] = np.copy(p.q[p.rope_index])
                p.l_0 = np.copy(p.l)
                p.tau_ffwd[p.rope_index] = 0
                p.pid.setPDjoint(p.rope_index, conf.robot_params[p.robot_name]['kp'][p.rope_index], conf.robot_params[p.robot_name]['kd'][p.rope_index], 0.)
                p.jumpNumber += 1
                # TODO for multiple jumps
                #p.startJump = p.time
                #p.pause_physics_client()
                break

        # send commands to gazebo
        p.send_des_jstate(p.q_des, p.qd_des, p.tau_ffwd)

        # log variables
        if (p.time > p.end_thrusting):
            p.logData()

        # plot  rope bw base link and anchor
        p.ros_pub.add_arrow(p.anchor_pos, (p.base_pos - p.anchor_pos), "green")
        p.ros_pub.add_marker(p.x_ee, radius=0.05)
        p.ros_pub.add_marker(p.anchor_pos + p.targetPos, color="red", radius=0.5)
        if (p.jumpNumber == p.numberOfJumps):
            p.ros_pub.add_marker(p.x_ee, color="green", radius=0.15)
        p.ros_pub.add_marker(p.x_ee, radius=0.05)
        p.ros_pub.add_arrow(p.x_ee, p.contactForceW / (10 * p.robot.robot_mass), "blue")
        p.ros_pub.publishVisual()

        # wait for synconization of the control loop
        rate.sleep()

        p.time = p.time + conf.robot_params[p.robot_name]['dt']

        # stops the while loop if  you prematurely hit CTRL+C
        if ros.is_shutdown():
            print("Shutting Down")
            break

    print("Shutting Down")
    ros.signal_shutdown("killed")
    p.deregister_node()
    p.plotStuff()


def plot3D(name, figure_id, label, time_log, var, time_mat = None, var_mat = None):
    fig = plt.figure(figure_id)
    fig.suptitle(name, fontsize=20)

    plt.subplot(3,1,1)
    plt.ylabel(label[0])
    plt.plot(time_log, var[0, :], linestyle='-', marker="o", markersize=0,  lw=5, color='red')
    if (var_mat is not None):
        plt.plot(time_mat, var_mat[0, :], linestyle='-', marker="o", markersize=0,  lw=5, color='blue')
    plt.grid()
    plt.legend(['sim', 'matlab'])

    plt.subplot(3,1,2)
    plt.ylabel(label[1])
    plt.plot(time_log, var[1, :], linestyle='-', marker="o", markersize=0,  lw=5, color='red')
    if (var_mat is not None):
        plt.plot(time_mat, var_mat[1, :], linestyle='-', marker="o", markersize=0,  lw=5, color='blue')
    plt.grid()
    plt.legend(['sim', 'matlab'])

    plt.subplot(3,1,3)
    plt.ylabel(label[2])
    plt.plot(time_log, var[2, :], linestyle='-', marker="o", markersize=0,  lw=5, color='red')
    if (var_mat is not None):
        plt.plot(time_mat, var_mat[2, :], linestyle='-', marker="o", markersize=0,  lw=5, color='blue')
    plt.grid()
    plt.legend(['sim', 'matlab'])

if __name__ == '__main__':
    p = ClimbingrobotController(robotName)

    try:
        talker(p)
    except ros.ROSInterruptException:
        p.plotStuff()
        pass


        
