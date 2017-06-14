import MalmoPython
import os
import sys
import time
import json
from controller import *
from math import *
from util import *

next_wid = 0


# data are key-value pairs, we can seach nodes for keys to exist, and store info at
# certain keys as well
class WaypointNode(object):
    def __init__(self, location, radius, data=None):
        global next_wid
        self.WID = next_wid
        next_wid += 1
        self.location = location
        self.radius = radius
        self.data = data
        if data is None:
            self.data = {}
        self.nodes = []

    def contains(self, point):
        x, y, z = self.location
        xp, yp, zp = point
        dx, dy, dz = x - xp, y - xp, z - zp
        return dx ** 2 + dy ** 2 + dz ** 2 <= self.radius ** 2

    def getAllNodes(self):
        """get all nodes in the graph this waypoint is part of"""
        """return : set(WaypointNode)"""
        discovered = set([self])
        discovered |= set(self.nodes)
        size = len(discovered)
        old_size = 0
        while (size != old_size):
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

    def assignNeighbor(self, neighbor, doPrint=False):
        """assign a neigbor to this waypoint graph"""
        if neighbor is None or self == neighbor:
            return
        if neighbor not in self.nodes:
            self.nodes.append(neighbor)
        if self not in neighbor.nodes:
            neighbor.nodes.append(self)

        if doPrint:
            print "added new connection %i - %i" % (self.WID, neighbor.WID)

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
    """returns the euclidian distance between 2 waypoints"""
    (x1, y1, z1) = wp1.location
    (x2, y2, z2) = wp2.location
    (dx, dy, dz) = (x2 - x1, y2 - y1, z2 - z1)
    return sqrt(dx ** 2 + dy ** 2 + dz ** 2)


def reconstruct(current, cameFrom):
    """reconstruct a path using the cameFrom dictionary and the last node in the route"""
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
    """perform the A* algorithm, to find a route from wpStart to wpEnd using a given heuristic"""
    """wpStart, wpEnd : WaypointNode, heuristic: (WaypointNode, WaypointNode) -> float"""
    """returns a list of waypoints, or None if no route was found"""
    # initialize
    closedSet = set()
    openSet = set([wpStart])
    cameFrom = {}
    gScore = {}
    gScore[wpStart] = 0
    fScore = {}
    fScore[wpStart] = heuristic(wpStart, wpEnd)
    # as long there are items in the open set
    while openSet:
        # select current node based on minimum f score
        current = min(openSet, key=lambda item: fScore.get(item, float("inf")))
        # if we reached the goal, reconstruct
        if current == wpEnd:
            return reconstruct(current, cameFrom)

        # move current node from open to closed set
        openSet.remove(current)
        closedSet.add(current)

        # discover new nodes
        for neighbor in current.nodes:
            if neighbor in closedSet:
                continue

            # evaluate g score of this neighbor
            gScore_t = gScore.get(current, float("inf")) + euclidianDistance(current, neighbor)

            # add the neighbor to the open set if it's not already in there,
            # if it's not, and it has a lower gScore, we don't have the
            # fastest route to this neighbor, so skip
            if neighbor not in openSet:
                openSet.add(neighbor)
            elif gScore_t >= gScore[neighbor]:
                continue

            # we found a (new fastest) way to the neighbor
            cameFrom[neighbor] = current
            gScore[neighbor] = gScore_t
            fScore[neighbor] = gScore_t + heuristic(neighbor, wpEnd)

    # we didn't find a route to wpEnd
    return None


def findRoute(startWp, endWp):
    """Find the route from the start waypoint to the end waypoint"""
    return Astar(startWp, endWp, euclidianDistance)


def findRoutesByKey(startWp, key):
    """Find the shortest routes from the start waypoint to all waypoints that contain a given key"""
    nodes = startWp.findNodes(key)
    return map(lambda node: Astar(startWp, node, euclidianDistance), nodes)


def findRouteByKey(startWp, key):
    """Find the shortest overall route from the start waypoint to a waypoint that contains given key"""
    routes = findRoutesByKey(startWp, key)
    route = min(routes, key=lambda route: len(route))
    return route


class Navigator(object):
    def __init__(self, controller):
        self.controller = controller
        self.enabled = True
        self.lastWaypoint = None  #: WaypointNode
        self.target = None  #: WaypointNode
        self.route = []  #: [WaypointNode]
        self.targetReached = False
        self.exploring = False

    def setRoute(self, route):
        self.route = route
        if len(self.route) == 0:
            self.target = None
            self.targetReached = True
        else:
            self.target = self.route.pop(0)
            self.targetReached = False

    def placeWaypoint(self, radius=4):
        wp = WaypointNode(self.controller.getLocation(), radius)
        wp.assignNeighbor(self.lastWaypoint)
        self.lastWaypoint = wp
        print "Placed new waypoint at ", wp.location, " with radius ", wp.radius

    def setBestNode(self, allNodes):
        bestNode = None
        distance = float("inf")
        wpHere = WaypointNode(self.Location, 0)
        for node in allNodes:
            dist = euclidianDistance(wpHere, node)
            if dist > node.radius:
                continue
            elif dist < distance:
                bestNode = node
                distance = dist
        self.lastWaypoint = bestNode

    def update(self):
        if not self.enabled:
            return
        if self.exploring:
            if self.lastWaypoint is None:
                self.placeWaypoint()
                return
            # in exploring mode, drop waypoints where you go
            if distanceH(self.lastWaypoint.location, self.controller.getLocation()) >= self.lastWaypoint.radius:
                allNodes = self.lastWaypoint.getAllNodes()
                newNode = True
                for node in allNodes:
                    if node == self.lastWaypoint:
                        continue
                    if node.contains(self.controller.getLocation()):
                        self.lastWaypoint.assignNeighbor(node)
                        newNode = False
                        break  # warning: can't handle overlapping nodes
                if newNode:
                    self.placeWaypoint()
                else:
                    self.setBestNode(allNodes)
            allNodes = self.lastWaypoint.getAllNodes()
            for node in allNodes:
                if distanceH(node.location, self.controller.getLocation()) <= node.radius:
                    self.lastWaypoint.assignNeighbor(node)

        elif self.target is not None:
            if distanceH(self.controller.getLocation(), self.target.location) < self.target.radius / 4:
                if len(self.route) > 0:
                    print "next target"
                    self.target = self.route.pop(0)
                else:
                    self.target = None
                    self.targetReached = True
                    self.controller.agent.sendCommand("move 0")

            if self.target is not None:
                (tx, ty, tz) = self.target.location
                self.controller.lookAtHorizontally2(self.target.location)
                self.controller.agent.sendCommand("move 1")
