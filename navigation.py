import MalmoPython
import os
import sys
import time
import json
from controller import *
from math import *
from util import *
import numpy as np


class Graph(object):
	def genNode(self, x, z, graph, defaultHeight):
		node = WaypointNode((int((x - self.width/2) * self.density), \
			defaultHeight,int((z - self.depth/2) * self.density)), 2.2, graph = graph)
		return node

	def __init__(self, width, depth, density, defaultHeight = 7):
		self.density = density
		self.width = width
		self.depth = depth
		self.enabledNodes = set()
		self.flaggedNodes = {} #dict key -> set(node)

		self.grid = np.array([[self.genNode(x, z, self, defaultHeight) \
			for z in range(depth)] for x in range(width)], dtype=object)


	def nodeIdAt(self, x, z):
		return (int((x / self.density) + self.width/  2), int((z / self.density) + self.depth/2))

	def getNode(self, idX, idZ):
		return self.grid[idX][idZ]

	def nodeIdAtLocation(self, loc):
		x, z = loc[0], loc[2]
		return self.nodeIdAt(x,z)

	def findNodes(self, key):
		ret = self.flaggedNodes.get(key)
		if ret is not None:
			return ret
		else:
			return set()


#data are key-value pairs, we can seach nodes for keys to exist, and store info at
#certain keys as well
class WaypointNode(object):
	def __init__(self, location, radius, graph = None):
		self.graph = graph
		self.location = location
		self.radius = radius
		self.enabled = False
		self.discovered = False

	def getFlags(self):
		flags = []
		for flag in self.graph.flaggedNodes:
			if self in self.graph.flaggedNodes[flag]:
				flags.append(flag)

		return flags


	def __repr__(self):
		return "<WAYPOINT loc {0}, rad {1}, en/disc {2}/{3}, flags {4}>". \
			format(self.location, self.radius, self.enabled, self.discovered, self.getFlags())

	def getNeighbors(self, filterNodes = True, goal = None):
		"""Get the neighbors of this node, you may filter for enabled nodes and disable the filter for the goal node"""
		if self.graph is None:
			return self.nodes
		else:
			idX, idZ = self.graph.nodeIdAtLocation(self.location)
			neighbors = []
			neighbors.append(self.graph.getNode(idX, idZ + 1))
			neighbors.append(self.graph.getNode(idX, idZ - 1))
			neighbors.append(self.graph.getNode(idX + 1, idZ + 1))
			neighbors.append(self.graph.getNode(idX + 1, idZ - 1))
			neighbors.append(self.graph.getNode(idX - 1, idZ + 1))
			neighbors.append(self.graph.getNode(idX - 1, idZ - 1))
			neighbors.append(self.graph.getNode(idX + 1, idZ))
			neighbors.append(self.graph.getNode(idX - 1, idZ))
			if filterNodes:
				return filter(lambda node: node.enabled or (node == goal and goal is not None), neighbors)
			else:
				return neighbors

	def enable(self):
		"""Enable this node"""
		if self.enabled:
			return
		self.enabled = True
		self.graph.enabledNodes.add(self)

	def disable(self):
		"""Disable this node"""
		if not self.enabled:
			return
		self.enabled = False
		self.graph.enabledNodes.remove(self)

	def contains(self, point):
		x, _, z = self.location
		xp, _, zp = point
		dx, dz = x - xp, z - zp
		return dx**2 + dz**2 <= self.radius**2

	def getAllNodes(self):
		return self.graph.enabledNodes()


	def setFlag(self, flag):
		if flag in self.graph.flaggedNodes:
			if self not in self.graph.flaggedNodes[flag]:
				self.graph.flaggedNodes[flag].add(self)
				print self

		else:
			self.graph.flaggedNodes[flag] = set([self])
			print self

def euclidianDistance(wp1, wp2):
	"""returns the euclidian distance between 2 waypoints"""
	(x1,y1,z1) = wp1.location
	(x2,y2,z2) = wp2.location
	(dx, dy, dz) = (x2 - x1, y2 - y1, z2 - z1)
	return sqrt(dx**2 + dy**2 + dz**2)


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
	#initialize
	'''https://en.wikipedia.org/wiki/A*_search_algorithm'''
	if not wpStart.enabled:
		print "Astar error, either start or end point isn't a valid node"
	closedSet = set()
	openSet = set([wpStart])
	cameFrom = {}
	gScore = {}
	gScore[wpStart] = 0
	fScore = {}
	fScore[wpStart] = heuristic(wpStart, wpEnd)
	#as long there are items in the open set
	while openSet:
		#select current node based on minimum f score
		current = min(openSet, key = lambda item: fScore.get(item, float("inf")))
		#if we reached the goal, reconstruct
		if current == wpEnd:
			return reconstruct(current, cameFrom)

		#move current node from open to closed set
		openSet.remove(current)
		closedSet.add(current)

		#discover new nodes
		for neighbor in current.getNeighbors(goal = wpEnd):
			if neighbor in closedSet:
				continue

			#evaluate g score of this neighbor
			gScore_t = gScore.get(current, float("inf")) + euclidianDistance(current, neighbor)

			#add the neighbor to the open set if it's not already in there,
			#if it's not, and it has a lower gScore, we don't have the
			#fastest route to this neighbor, so skip
			if neighbor not in openSet:
				openSet.add(neighbor)
			elif gScore_t >= gScore[neighbor]:
				continue

			#we found a (new fastest) way to the neighbor
			cameFrom[neighbor] = current
			gScore[neighbor] = gScore_t
			fScore[neighbor] = gScore_t + heuristic(neighbor, wpEnd)

	#we didn't find a route to wpEnd
	return None

def findRoute(startWp, endWp):
	"""Find the route from the start waypoint to the end waypoint"""
	return Astar(startWp, endWp, euclidianDistance)

def findRoutesByKey(startWp, key):
	"""Find the shortest routes from the start waypoint to all waypoints that contain a given key"""
	graph = startWp.graph
	nodes = list(graph.findNodes(key))
	return map(lambda node: Astar(startWp, node, euclidianDistance), nodes)

def findRouteByKey(startWp, key):
	"""Find the shortest overall route from the start waypoint to a waypoint that contains given key"""
	routes = findRoutesByKey(startWp, key)
	route = min(routes, key= lambda route:  len(route))
	return route


class Navigator(object):
	def __init__(self, controller):
		self.controller = controller
		self.enabled = True
		self.graph = None
		self.lastWaypoint = None #: WaypointNode
		self.target = None  #: WaypointNode
		self.route = [] #: [WaypointNode]
		self.targetReached = False
		self.exploring = False

	def setNavGraph(self, graph):
		self.graph = graph

	def setRoute(self, route):
		self.route = route
		if len(self.route) == 0:
			self.target = None
			self.targetReached = True
		else:
			self.target = self.route.pop(0)
			self.targetReached = False

	def placeWaypoint(self, radius = 4):
		wp = WaypointNode(self.controller.getLocation(), radius)
		wp.assignNeighbor(self.lastWaypoint)
		self.lastWaypoint = wp
		print "Placed new waypoint at ", wp.location, " with radius ", wp.radius

	def setBestNode(self,  allNodes):
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

	def updateFromVision(self, nonWalkable, interesting, visionRange):
		if interesting is not None:
			for loc, flag in interesting:
				blockLoc = loc + self.controller.location
				idX, idZ = self.graph.nodeIdAtLocation(blockLoc)
				node = self.graph.getNode(idX, idZ)
				node.setFlag(flag)

		for vX in range(-visionRange, visionRange + 1):
			for vZ in range(-visionRange, visionRange + 1):
				loc = self.controller.location + np.array([vX, 0, vZ])
				idX, idZ = self.graph.nodeIdAtLocation(loc)
				node = self.graph.getNode(idX, idX)
				node.enable()
				if not node.discovered:
					node.discovered = True
					print node

		if nonWalkable is not None:
			for loc in nonWalkable:
				blockLoc = loc + self.controller.location
				idX, idZ = self.graph.nodeIdAtLocation(blockLoc)
				node = self.graph.getNode(idX, idZ)
				node.disable()




	def update(self, autoMove):
		if not self.enabled:
			print "self not enabled, wut"
			return False

		idX, idZ = self.graph.nodeIdAtLocation(self.controller.location)
		self.lastWaypoint = self.graph.getNode(idX, idZ)
		if not self.lastWaypoint.enabled:
			self.lastWaypoint.enable()
			self.lastWaypoint.discovered = True

		if self.target == self.lastWaypoint or (self.target is not None and distanceH(self.target.location, self.lastWaypoint.location) < self.target.radius):

			if len(self.route) > 0:
				self.target = self.route.pop(0)
			else:
				self.targetReached = True
				if autoMove:
					self.controller.move(0)
				print "Target Reached!"
				self.target = None

		if self.target is not None:
			self.controller.lookAtHorizontally(self.target.location)
			if autoMove:
				self.controller.move(0.7)

		return True
