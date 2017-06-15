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
		self.controller.update(observation)
		self.visionHandler.updateFromObservation(observation[CUBE_OBS])
		self.playerPos = getPlayerPos(observation, False)
		self.intPlayerPos = getPlayerPos(observation, True)


	def findWood(self):
		""" See visionHandler.findBlocks function, returns coordinates of logs. """
		return self.visionHandler.findBlocks(BLOCK_WOOD)


	def destroyBlock(self, losDict, blockType, targetPosition = None):
		"""
		Destroys block(s) of the given blockType, at the given targetPosition.
		If targetPosition is not given, then the agent will first look around
		for blocks of that type, and destroy those. Otherwise, it will consult
		the waypoint graph. If the waypoint graph does not have the type, then
		False will be returned.

		TODO: Merge the waypoint graph consulting stuff

		This function will return 2 things every time it is called. It will
		return True if it succeeded in destroying a block or if it is currently
		in the process of doing so (there is no distinction...). It will return
		False if there are no more blocks to destroy of this type. This function
		should be called in the main loop.

		TODO: Figure out a way how to determine if a block is destroyed?

		"""

		# Find all the blocks in our visual vicinity, and use that as a basis
		# for the target position if it is not given, or use waypoint graph
		blockPositions = self.visionHandler.findBlocks(blockType)

		if targetPosition is None:
			if blockPositions != []:
				targetPosition = blockPositions[0] + self.intPlayerPos
			else:
				# TODO: Look for this block in the navigation/waypoint stuff...
				print "Not implemented yet! TODO: Add waypoint shit"
				return False

		# Figure out if target is in view distance, and thus figure out if we're
		# able to see and destroy the blocks
		distanceToTarget = distanceH(self.playerPos, targetPosition)
		movementSpeed = distanceToTarget / 3.0
		viewDistance = sqrt(3 * (CUBE_SIZE + 1)**2)

		if getVectorDistance(self.intPlayerPos, targetPosition) > viewDistance:
			# Target is outside our view distance, move towards it!
			# TODO: Use proper navigation
			print "Target is outside view distance, moving towards it! TODO: Use proper navigation..."
			self.controller.lookAt(targetPosition)
			self.controller.moveForward()
			return True

		if len(blockPositions) == 0:
			# Shit, no block visible/in range... either we got them all, or
			# there was nothing to begin with
			print "Target block {} at targetPosition {} not in visual range!".format(
				blockType, targetPosition)
			self.controller.setAttackMode(False)
			return False

		# Look at the first block
		usableBlockPos = self.intPlayerPos + blockPositions[0]
		realBlockPos = self.playerPos + blockPositions[0]
		self.controller.lookAt(realBlockPos)

		# Check line of sight to see if we have targeted the right block
		losBlock = getLineOfSightBlock(losDict)
		losBlockType = losDict[u"type"]
		relBlockPos = losBlock - self.intPlayerPos
		x, y, z = relBlockPos
		visionBlockIsCorrectType = self.visionHandler.isBlock(x, y, z, blockType)
		# print "losBlock = {}, losType = {}".format(losBlock, losBlockType)

		# If we are standing close enough to the target block, start
		# punching it,
		inRange = losDict[u"inRange"]

		if inRange and ((losBlock == usableBlockPos).all() or \
		visionBlockIsCorrectType or losBlockType == blockType):

			print "Destroying block!!!"
			self.controller.stopMoving()
			self.controller.lookAt(realBlockPos)
			self.controller.setAttackMode(True)
			return True
		else:
			# If the distance between the block and our position is too far
			# away, we need to move towards it
			self.controller.setAttackMode(False)
			distanceEpsilon = 0.9
			distanceToBlock = distanceH(self.playerPos, realBlockPos)

			# Malmo already clips speeds > 1.0 to 1.0 maximum
			movementSpeed = distanceToBlock / 3.0

			if distanceToBlock > distanceEpsilon:
				# Keep moving forward until we reach it
				print "Moving towards new block, possibly like a fucking moron!"
				self.controller.lookAt(realBlockPos)
				self.controller.moveForward(movementSpeed)

			return True

		# We've gotten all of the visible blocks at the targetPosition!
		print "Got all blocks {} at target position {}!".format(blockType, targetPosition)
		self.controller.setAttackMode(False)
		return False

		# TODO: Check log drops and pick them up

