import MalmoPython
import os
import sys
import time
import json
from controller import *
from math import *


#data are key-value pairs, we can seach nodes for keys to exist, and store info at
#certain keys as well
class WaypointNode(object):
    def __init__(self, location, radius, data = None):
        self.location = location
        self.radius = radius
        self.data = data
        if data is None:
            self.data = {}
        self.nodes = []

    def contains(self, point):
        x, y, z = location
        xp, yp, zp = point
        dx, dy, dz = x - xp, y - xp, z - zp
        return dx**2 + dy**2 + dz**2 <= self.radius**2

    def getAllNodes(self):
        """get all nodes in the graph this waypoint is part of"""
        discovered = set([self])
        discovered |= set(self.nodes)
        size = len(discovered)
        old_size = 0
        while(size != old_size):
            old_size = size
            disc2 = set()
            for node in discovered:
                disc2 |= set(node.nodes)
            discovered |= disc2
            size = len(discovered)
        return discovered

    def assignNeighbors(self, neighbors):
        """assign multiple neighbors to this node"""
        for n in neighbors:
            self.assignNeighbor(n)

    def assignNeighbor(self, neighbor):
        """assign a neigbor to this waypoint graph"""
        if neighbor not in self.nodes:
            self.nodes.append(neighbor)
        if self not in neighbor.nodes:
            neighbor.nodes.append(self)

    def detach(self):
        """remove this waypoint from the graph"""
        for node in self.nodes:
            if self in node.nodes:
                node.nodes.remove(self)

    def findNodes(self, key):
        allNodes = self.getAllNodes()
        newNodes = filter(lambda node: key in node.data, allNodes)
        return newNodes


def euclidianDistance(wp1, wp2):
    (x1,y1,z1) = wp1.location
    (x2,y2,z2) = wp2.location
    (dx, dy, dz) = (x2 - x1, y2 - y1, z2 - z1)
    return sqrt(dx**2 + dy**2 + dz**2)


def reconstruct(current, cameFrom):
    r = [current]
    while True:
        current = cameFrom.get(current)
        if current is None:
            break
        else:
            r.append(current)
    r.reverse()
    return r

def Astar(wpStart, wpEnd, heuristic):
    closedSet = set()
    openSet = set([wpStart])
    cameFrom = {}
    gScore = {}
    gScore[wpStart] = 0
    fScore = {}
    fScore[wpStart] = heuristic(wpStart, wpEnd)
    while openSet:
        current = min(openSet, key = lambda item: fScore.get(item, float("inf")))
        if current == wpEnd:
            return reconstruct(current, cameFrom)

        openSet.remove(current)
        closedSet.add(current)
        for neighbor in current.nodes:
            if neighbor in closedSet:
                continue
            gScore_t = gScore.get(current, float("inf")) + euclidianDistance(current, neighbor)
            if neighbor not in openSet:
                openSet.add(neighbor)
            elif gScore_t >= gScore[neighbor]:
                continue
            cameFrom[neighbor] = current
            gScore[neighbor] = gScore_t
            fScore[neighbor] = gScore_t + heuristic(neighbor, wpEnd)

    return None

def findRoute(startWp, endWp):
    return Astar(startWp, endWp, euclidianDistance)

def findRoutesByKey(startWp, key):
    nodes = startWp.findNodes(key)
    return map(lambda node: Astar(startWp, node, euclidianDistance), nodes)

def findRouteByKey(startWp, key):
    routes = findRoutesByKey(startWp, key)
    route = min(routes, key= lambda route:  len(route))
    return route


class Navigator(object):
    def __init__(self, controller):
        self.controller = controller
        self.enabled = True
        self.lastWaypoint = None #: WaypointNode
        self.target = None  #: WaypointNode
        self.route = [] #: [WaypointNode]
        self.targetReached = False
        self.exploring = False

    def setRoute(self, route):
        self.route = route
        self.target = self.route.pop(0)

    def update(self):
        if not self.enabled:
            return
        if self.exploring:
            #in exploring mode, drop waypoints where you go
            if distanceH(self.lastWaypoint.location, self.controller.Location) >= 8.5:
                allNodes = self.lastWaypoint.getAllNodes()
                newNode = True
                for node in allNodes:
                    if node.contains(self.controller.Location):
                        self.lastWaypoint.assignNeighbor(node)
                        self.lastWaypoint = node
                        newNode = False
                        break #warning: can't handle overlapping nodes
                if newNode:
                    wp = WaypointNode(self.controller.Location, 2)
                    self.lastWaypoint = wp
                    wp.assignNeighbor(self.lastWaypoint)

        else:
            if distanceH(self.controller.Location, self.target.location) < self.target.radius:
                self.controller.agent.sendCommand("move 0")
                if self.route is not []:
                    self.target = self.route.pop(0)
                else:
                    self.target = None
                    self.targetReached = True

            if self.target is not None:
                (tx, ty, tz) = self.target.Location
                self.controller.lookAtH(tx, tz)
                self.controller.agent.sendCommand("move 1")

