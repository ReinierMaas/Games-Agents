import MalmoPython
import os
import sys
import time
import json
from controller import *
from math import *

class Beacon(object):
    def __init__(self, location, radius):
        self.location = location
        self.radius = radius

class TreeNode(object):
    def __init__(self, name = None, data = None, parent = None):
        self.name = name
        self.nodes = []
        self.data = data
        if parent is not None:
            parent.nodes.append(self)


    def findNode(self, name):
        if self.name == name:
            return self
        else:
            #breath-first search for the correct node
            for node in self.nodes:
                if node.name == name:
                    return node
            for node in self.nodes:
                node.findNode(name)

class Navigator(object):
    def __init__(self, controller):
        self.controller = controller
        self.enabled = True
        self.navTree = None
        #target and are beacons
        self.target = None
        self.route = []
        self.targetReached = False


    def setRoute(self, beacons):
        self.route = beacons
        self.target = self.route.pop(0)

    def update(self):
        if not self.enabled:
            return

        if distanceH(self.controller.Location, self.target.location) < self.target.radius:
            self.controller.agent.sendCommand("move 0")
            if self.route is not []:
                self.target = self.route.pop(0)
            else:
                self.target = None
                self.targetReached = True

        if self.target is not None:
            self.controller.lookAtH(target.x, target.z)
            self.controller.agent.sendCommand("move 1")

