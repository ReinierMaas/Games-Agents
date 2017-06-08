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
	def __init__(self, width, height, depth, heightOffset = 0):
		self.heightOffset = heightOffset
		self.width, self.height, self.depth = width, height, depth
		self.grid = np.array([[[WaypointNode((x - int(width/2),y + heightOffset,z - int(depth/2)), sqrt(2), graph = self) for z in range(depth) ] for y in range(height)] for x in range(width)], dtype=object)
		self.enabledNodes = set()
		self.flaggedNodes = {} #dict key -> set(node)

	def nodeAt(self, x, y, z):
		return self.grid[int(x) + int(self.width/2)][int(y) - int(self.heightOffset)][int(z) + int(self.depth/2)]

	def nodeAtLocation(self, loc):
		x, y, z = loc[0], loc[1], loc[2]
		return self.nodeAt(x,y,z)

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

	def getNeighbors(self, filterNodes = True, goal = None):
		"""Get the neighbors of this node, you may filter for enabled nodes and disable the filter for the goal node"""
		if self.graph is None:
			return self.nodes
		else:
			x, y, z = self.location[0], self.location[1], self.location[2]
			neighbors = []
			for ix in range(-1, 2):
				for iy in range(-1, 2):
					for iz in range(-1, 2):
						neighbors.append(self.graph.nodeAt(ix, iy, iz))
			neighbors.remove(self)
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
		x, y, z = self.location
		xp, yp, zp = point
		dx, dy, dz = x - xp, y - xp, z - zp
		return dx**2 + dy**2 + dz**2 <= self.radius**2

	def getAllNodes(self):
		return self.graph.enabledNodes()
		# """get all nodes in the graph this waypoint is part of"""
		# """return : set(WaypointNode)"""
		# discovered = set([self])
		# discovered |= set(self.nodes)
		# size = len(discovered)
		# old_size = 0
		# while(size != old_size):
		# 	old_size = size
		# 	disc2 = set()
		# 	for node in discovered:
		# 		disc2 |= set(node.nodes)
		# 	discovered |= disc2
		# 	size = len(discovered)
		# return discovered

	def assignNeighbors(self, neighbors):
		pass
		"""assign multiple neighbors to this node"""
		for n in neighbors:
			self.assignNeighbor(n)

	def assignNeighbor(self, neighbor, doPrint = False):
		pass
		"""assign a neigbor to this waypoint graph"""
		if neighbor is None or self == neighbor:
			return
		if neighbor not in self.nodes:
			self.nodes.append(neighbor)
		if self not in neighbor.nodes:
			neighbor.nodes.append(self)

		if doPrint:
			print "added new connection %i - %i" % (self.WID, neighbor.WID)

	def setFlag(self, flag):
		if flag in self.graph.flaggedNodes:
			self.graph.flaggedNodes[flag].add(self)
		else:
			self.graph.flaggedNodes[flag] = set([self])

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
	if not wpStart.enabled or not wpEnd.enabled:
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
	nodes = graph.findNodes(key)
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

	def updateFromVision(self, walkable, interesting):
		if walkable is not None:
			for loc in walkable:
				blockLoc = loc + self.controller.location
				node = self.graph.nodeAtLocation(blockLoc)
				node.enable()
		if interesting is not None:
			for loc, flag in interesting:
				blockLoc = loc + self.controller.location
				node = self.graph.nodeAtLocation(blockLoc)
				node.setFlag(flag)


	def update(self, autoMove):
		if not self.enabled:
			return

		lastWaypoint = self.graph.nodeAtLocation(self.controller.location)
		"""
		if self.exploring:
			if self.lastWaypoint is None:
				self.placeWaypoint()
				return
			#in exploring mode, drop waypoints where you go
			if distanceH(self.lastWaypoint.location, self.controller.getLocation()) >= self.lastWaypoint.radius:
				allNodes = self.lastWaypoint.getAllNodes()
				newNode = True
				for node in allNodes:
					if node == self.lastWaypoint:
						continue
					if node.contains(self.controller.getLocation()):
						self.lastWaypoint.assignNeighbor(node)
						newNode = False
						break #warning: can't handle overlapping nodes
				if newNode:
					self.placeWaypoint()
				else:
					self.setBestNode(allNodes)
			allNodes = self.lastWaypoint.getAllNodes()
			for node in allNodes:
				if distanceH(node.location, self.controller.getLocation()) <= node.radius:
					self.lastWaypoint.assignNeighbor(node)

		elif self.target is not None:"""
		if not self.exploring and self.target is not None:
			if distanceH(self.controller.getLocation(), self.target.location) < self.target.radius:
				if len(self.route) > 0:
					print "next target"
					self.target = self.route.pop(0)
				else:
					self.target = None
					self.targetReached = True
					if autoMove:
						self.controller.move(0)

			if self.target is not None:
				self.controller.lookAtHorizontally2(self.target.location)
				if autoMove:
					self.controller.move(1)

