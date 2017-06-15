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
		self.entitiesHandler = EntitiesHandler()
		self.controller = Controller(agentHost)


	def updateObservation(self, observation):
		""" Updates handlers with observations. """
		self.controller.update(observation)
		self.visionHandler.updateFromObservation(observation)
		self.entitiesHandler.updateFromObservation(observation)
		self.playerPos = getPlayerPos(observation, False)
		self.intPlayerPos = getPlayerPos(observation, True)


	def destroyBlock(self, losDict, blockType, targetPosition = None):
		"""
		Destroys block(s) of the given blockType, at the given targetPosition.
		If targetPosition is not given, then the agent will look around	for
		blocks of that type, and destroy those. Otherwise, it will consult the
		waypoint graph. If the waypoint graph does not have the type, then
		False will be returned.

		TODO: Merge the waypoint graph consulting stuff

		This function will return True/False every time it is called. It will
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
		movementSpeed = distanceToTarget / 3.5
		viewDistance = sqrt(3 * (CUBE_SIZE + 1)**2)

		if getVectorDistance(self.intPlayerPos, targetPosition) > viewDistance:
			# Target is outside our view distance, move towards it!
			# TODO: Use proper navigation
			# print "Target is outside view distance, moving towards it!"
			self.controller.lookAt(targetPosition)
			self.controller.moveForward()
			return True

		if len(blockPositions) == 0:
			# Check if we are "close" enough to the target position, and
			# if so, then that means that there are now no blocks visible/in
			# range, so either we got them all, or there was nothing at all.
			# If we are not close enough, then we should move closer to the
			# target position and try again
			self.controller.setAttackMode(False)

			if distanceToTarget > sqrt(2.0):
				# print "Returning back to target position {}".format(targetPosition)
				self.controller.lookAt(targetPosition)
				self.controller.moveForward(movementSpeed)
				return True
			else:
				# print "Target block {} at targetPosition {} not in visual range!".format(
					# blockType, targetPosition)
				# print "Either we got them all, or there was nothing to begin with..."
				return False

		# Look at the first block (they are sorted based on distance to player)
		usableBlockPos = self.intPlayerPos + blockPositions[0]
		realBlockPos = self.playerPos + blockPositions[0]
		self.controller.lookAt(realBlockPos)

		# Check line of sight to see if we have targeted the right block
		losBlock = getLineOfSightBlock(losDict)
		losBlockType = losDict[u"type"]
		relBlockPos = losBlock - self.intPlayerPos
		x, y, z = relBlockPos
		visionBlockIsCorrectType = self.visionHandler.isBlock(x, y, z, blockType)

		# If we are close enough to the target block, start punching it
		inRange = losDict[u"inRange"]

		if inRange and ((losBlock == usableBlockPos).all() or \
		visionBlockIsCorrectType or losBlockType == blockType):

			# print "Destroying block!!!"
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
				# print "Moving towards new block, possibly like a fucking moron!"
				self.controller.lookAt(realBlockPos)
				self.controller.moveForward(movementSpeed)

			return True



	def collectDrops(self, dropType):
		"""
		Collects dropped items by walking over to them. This function should be
		called in a loop, just like destroyBlock(). It returns True for as long
		as there are drops to collect, and False when there are no more drops.
		"""

		# Check if we can collect some drops, and pick them up...
		dropPositions = self.entitiesHandler.getEntityPositions(dropType)

		if len(dropPositions) != 0:
			self.controller.lookAt(dropPositions[0])
			self.controller.moveForward()
			return True
		else:
			return False
