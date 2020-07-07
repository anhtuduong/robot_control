
import pinocchio as pin
import numpy as np
import example_robot_data
from pinocchio.utils import * #rand
from pinocchio.robot_wrapper import RobotWrapper
from pinocchio.utils import *


# console print options to see matrix nicely
np.set_printoptions(precision = 3, linewidth = 200, suppress = True)
np.set_printoptions(threshold=np.inf)

# Loading a robot model
model = example_robot_data.loadHyQ().model
data = model.createData()

#start configuration
v  = np.array([0.0   ,  0.0 , 0.0,  0.0,  0.0,       0.0, #underactuated 	
		     0.0,  0.0,  0.0,  0.0,     0.0,  0.0,  0.0,  0.0,  0.0,    0.0,  0.0,  0.0]) #actuated
q = example_robot_data.loadHyQ().q0

# Update the joint and frame placements
pin.forwardKinematics(model,data,q,v)
pin.updateFramePlacements(model,data)

M =  pin.crba(model, data, q)
H = pin.nonLinearEffects(model, data, q, v)
G = pin.computeGeneralizedGravity(model,data, q)

#EXERCISE 1: Compute the com of the robot (in WF)
mass_robot = 0
w_com_robot =np.zeros((3))
for idx,name in enumerate(model.joints): 
	if (idx>0): #skip the first universe link		 

		mass_link = model.inertias[idx].mass
		mass_robot+= mass_link
		#com_link = data.oMi[idx].act(model.inertias[idx].lever)				
		com_link =  model.inertias[idx].lever		
		w_com_link = data.oMi[idx].rotation.dot(com_link) + data.oMi[idx].translation		
		w_com_robot +=  mass_link * w_com_link
w_com_robot /=mass_robot
print "Com Position w_com_robot: ", w_com_robot
# compute using native pinocchio function
com_test = pin.centerOfMass(model, data, q, v)
print "Com Position (pinocchio): ", com_test

# EXERCIZE 2 : Compute robot kinetic energy
#get a random generalized velocity 
#v = rand(model.nv)
## Update the joint and frame placements
#pin.forwardKinematics(model,data,q,v)
## compute using generalized velocities and system mass matrix
#EkinRobot = 0.5*v.transpose().dot(M.dot(v))
#
## compute using separate link contributions using spatial algebra
#EKinSystem= 0
##get the spatial velocities of each link
#twists = [f for f  in data.v]
#inertias = [f for f  in model.inertias]
#for idx, inertia in enumerate(inertias):
#	EKinSystem += inertias[idx].vtiv(twists[idx]) # twist x I twist
#EKinSystem *= .5;
#print "TEST1: ", EkinRobot - EKinSystem
## use pinocchio native function
#pin.computeKineticEnergy(model,data,q,v)
#print "TEST2: ", EkinRobot - data.kinetic_energy


##EXERCIZE 3: Build the transformation matrix to use com coordinates
## get the location of the base frame
#w_base = data.oMi[1].translation
##compute centroidal quantitities (hg, Ag and Ig)
#pin.ccrba(model, data, q, v)
##print "Base Position w_base  ", w_base
#G_T_B = np.zeros((model.nv, model.nv))
#G_Tf_B = np.zeros((model.nv, model.nv))
#G_X_B = np.zeros((6, 6))
#
##G_X_B =
#G_X_B[:3,:3] = np.eye(3)
#G_X_B[3:,3:] = np.eye(3)
#G_X_B[:3,3:] = pin.skew(com_test - w_base)
#G_Xf_B = np.linalg.inv(G_X_B.T)
#
#F_B = M[:6, 6:]
#S_G_B = np.linalg.inv(data.Ig).dot(G_Xf_B.dot(F_B))
##G_T_B
#G_T_B[:6 , :6] = G_X_B
#G_T_B[6: , 6:] = np.eye(12)
#G_T_B[:6 , 6:] = S_G_B
#
##G_Tf_B
#G_Tf_B[:6 , :6] = G_Xf_B
#G_Tf_B[6: , 6:] = np.eye(12)
#G_Tf_B[6: , :6] = -(S_G_B.T).dot(G_Xf_B)
#
##check G_Tf_B = inv(G_T_B.T)
##print np.linalg.inv(G_T_B.T) - G_Tf_B


# EXERCISE 4: Check the mass matrix becomes block diagonal
#M_g = G_Tf_B * M * np.linalg.inv(G_T_B)
#print "\n The mass matrix expressed at the com becomes diagonal: \n", M_g


# EXERSISE 5: Check that joint gravity vector nullifies
#Grav_W = np.hstack( ( np.array((0.0, 0.0, -9.81)), np.zeros( model.nv - 3)  )).T
##G_g = G_Tf_B.dot(G) (TODO does not work)
#G_g = -M_g.dot(Grav_W) 

#the fact that all become zero it makes sense if you think the com is not a point solidal with the base link
# but moves with joints, this means that its jacobians has a part from the base and from the joints. 
# so if we try to turn the floating base robot to a fixed base applying the wrench of "God" 
# we will have also an influence on the joint torques that will be cancelled
#print "\n The gravity force vector at the com should be  [0 0 mg   03x1    0nx1 ]: \n", G_g
 