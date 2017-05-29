
#use observation from ray to determine if a block to destroy has been broken:
#the coordinate should change when a block is broken!


#assumes:
#<ObservationFromFullStats/>
#<ContinuousMovementCommands turnSpeedDegs="180"/>
#observations.get(u'Yaw', 0)

import MalmoPython
import os
import sys
import time
import json
from math import *

def shortAngle(a1, a2):
    """calculate the shortest signed angle from a1 to a2"""
    x,y = radians(a1), radians(a2)
    a = atan2(sin(x-y), cos(x-y))
    return degrees(a)

def distanceH(v1, v2):
    """calculate the horizontal distance between 2 vectors"""
    (x1, _, z1) = v1
    (x2, _, z2) = v2
    dx = x1 - x2
    dz = z1 - z2
    return sqrt(dx**2 + dz**2)

cam_speed = 0.7
lookV_speed = cam_speed/180.0
turn_speed = cam_speed/180.0

class Controller(object):

    def __init__(self, agent):
        self.agent = agent
        self.currentHotbar = 0
        self.Yaw = 0
        self.Pitch = 0
        self.Location = (0,0,0)
        self.cam_move_threshold = 2

    def update(self, observations):
        """get world state, read out relevant observations"""
        if observations is not None:
            self.Yaw = observations.get(u'Yaw', 0)
            self.Pitch = observations.get(u'Pitch', 0)
            self.Location = (observations.get(u'XPos', 0), \
                observations.get(u'YPos', 0), observations.get(u'ZPos', 0))

    def selectHotbar(self, hotbar):
        """select a given hotbar"""
        self.agent.sendCommand("hotbar.%i 1" % hotbar)
        self.agent.sendCommand("hotbar.%i 0" % hotbar)
        currentHotbar = hotbar


    def pitch(self, angle):
        """pitch by a given angle (approx)"""
        self.setPitch(self.Pitch + angle)


    def turn(self, angle):
        """pitch by a given angle (approx)"""
        self.setYaw(self.Yaw + angle)

    def setYaw(self, newYaw):
        """look at a given yaw value"""
        if int(self.Yaw) == int(newYaw):
            return
        print "set new yaw:", newYaw
        self.agent.sendCommand("setYaw %f" % newYaw)

    def setPitch(self, newPitch):
        """look at a given pitch value"""
        if self.Pitch == newPitch:
            return
        print "set new pitch:", newYaw
        self.agent.sendCommand("setPitch %f" % newPitch)

    def lookAtHorizontally(self, x, z):
        """face a given location (requires observing current position of the agent)"""
        (cx,_,cz) = self.Location
        (dx,dz) = (cx - x, cz - z)
        yw = degrees(atan2(dz, dx)) + 90
        self.setYaw(yw)

    def lookAtHorizontally2(self, tup):
        """face a given location in 3D vector tuple form"""
        (x,_,z) = tup
        self.lookAtHorizontally(x,z)
