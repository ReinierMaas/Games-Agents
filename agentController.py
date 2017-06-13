# Main code for handling the agent and doing stuff like choppping trees

# Assumes:
# <ObservationFromFullStats/>
# <ContinuousMovementCommands turnSpeedDegs="180"/>
# observations.get("Yaw", 0)

import MalmoPython
import numpy as np
import time

from util import *
from math import *
from controller import *
from vision import *


class AgentController(object):
	""" Class used for controlling agent. """

	def __init__(self, agentHost):
		self.agent = agentHost
		self.visionHandler = VisionHandler(CUBE_SIZE)
		self.controller = Controller(agentHost)


	def updateObservation(self, observation):
		""" Updates handlers with observations. """
		self.observation = observation
		self.controller.update(observation)
		self.visionHandler.updateFromObservation(observation[CUBE_OBS])
		self.playerPos = getPlayerPos(observation, False)
		self.intPlayerPos = getPlayerPos(observation, True)


	def findWood(self):
		""" See visionHandler.findBlocks function, returns coordinates of logs. """
		return self.visionHandler.findBlocks(BLOCK_WOOD)


	def chopTree(self, treePosition = None):
		"""
		Chops down 1 tree and collects all the logs from that tree. If no tree
		position is given (np array with x, y, z position), then the agent
		looks in his direct surroundings for a tree, and will chop that one
		down. If no trees are in his direct surroundings, he will explore the
		navigation/waypoint graph for a tree, go there, and chop that one down.
		Finally, it will return True if it succeeded in chopping down a part of
		the tree, and False if it failed to chop it down or if it is already
		fully chopped down. This function should be called in a loop.
		"""

		# Find all the wood in our vicinity, also useful for later
		woodPositions = self.findWood()

		if treePosition is None:
			if woodPositions != []:
				treePosition = woodPositions[0]
			else:
				# TODO: Look a tree in the navigation/waypoint stuff...
				print "Not implemented yet!"
				return False

		# Check if we have the tree targeted in our LOS, and if its in range
		distanceToTree = distanceH(self.playerPos, treePosition)
		movementSpeed = distanceToTree / 3.0

		if u"LineOfSight" in self.observation:
			lineOfSightDict = self.observation[u"LineOfSight"]
			losBlock = getLineOfSightBlock(lineOfSightDict)

			if (losBlock == treePosition).all():
				# Yes, we have it targeted, check if its in range and if its wood
				inRange = lineOfSightDict[u"inRange"]
				losBlockType = lineOfSightDict[u"type"]

				if inRange:
					if losBlockType == BLOCK_WOOD:
						# Stop moving and chop it down
						self.controller.stopMoving()
						self.controller.setAttackMode(True)
					else:
						# In range but not wood, keep moving?
						# TODO: Figure out something smarter, aka navigation
						self.controller.lookAt(treePosition)
						self.controller.moveForward(movementSpeed)

		# Check distance to tree and move towards it
		self.controller.lookAt(treePosition)
		self.controller.moveForward(movementSpeed)

		# Look at the first wood block
		usableWoodPos = usablePlayerPos + woodPositions[0]
		realWoodPos = playerPos + woodPositions[0]
		tempx, tempy, tempz = woodPositions[0]
		controller.lookAt(realWoodPos)

		# Check line of sight to see if we have targeted the right block
		if u"LineOfSight" in observation:
			lineOfSightDict = observation[u"LineOfSight"]
			losBlock = getLineOfSightBlock(lineOfSightDict)
			relBlockPos = losBlock - usablePlayerPos
			x, y, z = relBlockPos
			visionBlockIsWood = visionHandler.isBlock(x, y, z, BLOCK_WOOD)
			losBlockType = lineOfSightDict[u"type"]

			# If we are standing close enough to the wood block, start
			# punching it,
			inRange = lineOfSightDict[u"inRange"]

			if inRange and ((losBlock == usableWoodPos).all() or visionBlockIsWood \
			or losBlockType == BLOCK_WOOD):

				print "Chopping tree down!!!!"
				agentHost.sendCommand("move 0")
				controller.lookAt(realWoodPos)
				agentHost.sendCommand("attack 1")
			else:
				# If the distance between the wood block and our position
				# is too far away, we need to towards it
				agentHost.sendCommand("attack 0")
				distanceEpsilon = 0.9
				distanceToWood = distanceH(playerPos, realWoodPos)

				# Malmo already clips speeds > 1.0 to 1.0 maximum
				movementSpeed = distanceToWood / 3.0

				if distanceToWood > distanceEpsilon:
					# Keep moving forward until we reach it
					print "Moving towards new wood, possibly like a fucking moron! Speed = {}".format(
						movementSpeed)
					agentHost.sendCommand("move {}".format(movementSpeed))

		# Then we collect the log spoils

