
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
        self.observations = None

    def update(self):
        """get world state, read out relevant observations"""
        world_state = self.agent.getWorldState()
        for error in world_state.errors:
            print "Error:",error.text
        if len(world_state.observations) > 0:
            msg = world_state.observations[-1].text
            self.observations = json.loads(msg)
            self.Yaw = self.observations.get(u'Yaw', 0)
            self.Pitch = self.observations.get(u'Pitch', 0)
            self.Location = (self.observations.get(u'XPos', 0), \
            self.observations.get(u'YPos', 0), self.observations.get(u'ZPos', 0))

    def selectHotbar(self, hotbar):
        """select a given hotbar"""
        self.agent.sendCommand("hotbar.%i 1" % hotbar)
        self.agent.sendCommand("hotbar.%i 0" % hotbar)
        currentHotbar = hotbar

    def pitch(self, angle):
        """pitch by a given angle (approx)"""
        self.agent.sendCommand("pitch %f" % (float(angle) * lookV_speed))
        time.sleep(1/cam_speed)
        self.agent.sendCommand("pitch 0")


    def turn(self, angle):
        """pitch by a given angle (approx)"""
        self.agent.sendCommand("turn %f" % (float(angle) * turn_speed))
        time.sleep(1/cam_speed)
        self.agent.sendCommand("turn 0")

    def lookH(self, newYaw):
        """look at a given yaw value (approx)"""
        diff = shortAngle(newYaw, self.Yaw)
        print "lookH", diff
        self.turn(diff)

    def lookV(self, newPitch):
        """look at a given pitch value (approx)"""
        diff = shortAngle(newPitch, self.Pitch)
        print "lookV", diff
        self.pitch(diff)

    def lookAtH(self, x, z):
        """face a given location (requires observing current position of the agent)"""
        (cx,_,cz) = self.Location
        (dx,dz) = (cx - x, cz - z)
        yw = degrees(atan2(dz, dx)) + 90
        self.lookH(yw)

    def lookAtH2(self, tup):
        """face a given location in 3D vector tuple form"""
        (x,_,z) = tup
        self.lookAtH(x,z)

