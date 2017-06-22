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
from vision import *
from inventory import *
from controller import *
import navigation as nav



# Keys to use for the losProp dict, see destroyBlock() function
LOS_PROP_NAME = "name"
LOS_PROP_VALUE = "value"



class AgentController(object):
	""" Class used for controlling agent. """

	def __init__(self, agentHost):
		self.agent = agentHost
		self.visionHandler = VisionHandler(CUBE_SIZE)
		self.entitiesHandler = EntitiesHandler()
		self.controller = Controller(agentHost)
		self.navigator = nav.Navigator(self.controller)
		self.inventoryHandler = InventoryHotbar()
		self.goap = None

		# We keep track of the losProp and the list of "banned" blocks to allow
		# destroyBlock() function to keep track of which blocks do not match
		# the given, named property value in the losDict (e.g. fully grown wheat).
		# The list is emptied when no more visible blocks of the given blockType
		# are within range, or if losProp, targetPosition or blockType change,
		# so we can try if the properties match again.
		self.__resetBannedState()


	def updateObservation(self, observation):
		""" Updates handlers with observations. """
		self.losDict = observation.get(u"LineOfSight", None)
		self.controller.update(observation)
		self.visionHandler.updateFromObservation(observation)
		self.entitiesHandler.updateFromObservation(observation)
		self.inventoryHandler.updateFromObservation(observation)
		self.playerPos = getPlayerPos(observation, False)
		self.intPlayerPos = getPlayerPos(observation, True)

		if self.goap is not None:
			self.goap.updateState()


	def __resetBannedState(self, blockType = None, targetPosition = None, losProp = None):
		""" Helper function that resets the state used for destroyBlock. """
		self.__blockType = blockType
		self.__targetPosition = targetPosition
		self.__losProp = losProp
		self.__bannedBlocks = []


	def __blockIsBanned(self, blockPos):
		""" Returns True/False if the given block is banned. """
		for bannedBlock in self.__bannedBlocks:
			if (bannedBlock == blockPos).all():
				return True

		return False


	def destroyBlock(self, blockType, targetPosition = None, losProp = None):
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

		Optionally, the losProp parameter can be set to a dictionairy, with 2
		keys (LOS_PROP_NAME and LOS_PROP_VALUE), indicating the exact properties
		of the block that will be destroyed. Example of a losProp dict:
			{
				LOS_PROP_NAME: "prop_age",		# Name of the property in losDict
				LOS_PROP_VALUE: 7,				# Value of the property in losDict
			}

		If the targeted block does not have this property, or if the values do
		not match exactly, the block will be ignored.

		TODO: Figure out a way how to determine if a block is destroyed?
		(Possible solution: use inventor checks and/or entitiesHandler...)

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
		relTargetPos = np.floor(targetPosition).astype(int) - self.intPlayerPos
		x, y, z = relTargetPos

		if not self.visionHandler.inVisionRange(x, y, z):
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

		# Check line of sight to see if we have targeted the right block
		if self.losDict is None:
			self.controller.setPitch(45)	# Look at ground to get LOS dict
			return True

		# Get line of sight details
		losBlock = getLineOfSightBlock(self.losDict)
		losBlockType = self.losDict[u"type"]
		relBlockPos = losBlock - self.intPlayerPos
		x, y, z = relBlockPos

		visionBlockIsCorrectType = self.visionHandler.isBlock(x, y, z, blockType)

		# Check if the properties match, if any
		if losProp is not None and losBlockType == blockType:
			# Skip this block if the properties don't match
			propName = losProp[LOS_PROP_NAME]

			if propName not in self.losDict or losProp[LOS_PROP_VALUE] != self.losDict[propName]:
				# If this is the first time we ban this blockType at the given
				# targetPosition with the given losProp, update state
				# print "self: losProp = {}, blockType = {}, targetPosition = {}".format(
				# 	self.__losProp, self.__blockType, self.__targetPosition)
				# print "args: losProp = {}, blockType = {}, targetPosition = {}".format(
				# 	losProp, blockType, targetPosition)
				if self.__losProp != losProp or self.__blockType != blockType or \
				(self.__targetPosition != targetPosition).any():

					print "Resetting losProp state stuff! (1)"
					self.__resetBannedState(blockType, targetPosition, losProp)

				# Add it to banned blocks list if its not already in there
				if not self.__blockIsBanned(losBlock):
					print "banning block at {} with type = {}".format(losBlock,
						losBlockType)
					self.__bannedBlocks.append(losBlock)

				print "banned blocks = {}".format(self.__bannedBlocks)

				# Check if we have any valid, visible blocks left at all...
				validBlocks = [False] * len(blockPositions)

				for i in range(len(blockPositions)):
					blockPos = self.intPlayerPos + blockPositions[i]
					validBlocks[i] = not self.__blockIsBanned(blockPos)

					if validBlocks[i]:
						break

				if np.array(validBlocks).any():
					return True
				else:
					print "No valid blocks left!"
					return False

		# Look at the first non-banned block (they are sorted based on distance to player)
		relBlock = None

		for block in blockPositions:
			if not self.__blockIsBanned(self.intPlayerPos + block):
				relBlock = block
				break

		# Check if we have actually found a valid block, and if not, delete
		# banned blocks state and return False
		if relBlock is None:
			self.__resetBannedState()
			print "Resetting losProp state stuff! (2)"
			return False

		usableBlockPos = self.intPlayerPos + relBlock
		realBlockPos = self.playerPos + relBlock
		self.controller.lookAt(realBlockPos)

		# If we are close enough to the target block, start punching it
		inRange = self.losDict[u"inRange"]

		if inRange and ((losBlock == usableBlockPos).all() or visionBlockIsCorrectType \
		or losBlockType == blockType) and not self.__blockIsBanned(realBlockPos):

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



	def placeBlock(self, targetPosition, jumpOnPlacement = False):
		"""
		If the agent is currently holding a block (check it yourself), then this
		function will attempt to place that block exactly on the targetPosition.
		Since Malmo's LineOfSight coordinates are as thrustworthy as the local
		homeless crack-addicted whores on heroine, we walk over to the target
		position and then place the block below our feet. Optionally, the agent
		can be made to jump on placing the block. Note that Malmo does not
		distinguish between placing a block and using e.g. a door... Because
		obviously that makes total sense.

		Note that this function works the opposite of destroyBlock(), it will
		return False until it has actually placed the block, after that moment
		it will return True
		"""

		# Check distance to targetPosition and navigate towards it
		distanceToTarget = distanceH(self.playerPos, targetPosition)
		movementSpeed = distanceToTarget / 2.0
		closeEnough = 0.3

		if distanceToTarget > closeEnough:
			# Target is not below our feet, move towards it!
			# TODO: Use proper navigation
			# print "Target is not below our feet, moving towards it!"
			self.controller.lookAt(targetPosition)
			self.controller.moveForward(movementSpeed)
			return False

		# Look down at it and place the block
		self.controller.stopMoving()
		self.controller.lookAt(targetPosition)

		if jumpOnPlacement:
			print "JUMP! TODO: Finish jump"

		self.controller.placeBlock()
		return True


	def useItem(self, targetPosition, jumpOnUse = False):
		"""
		Malmo does not differentiate between placing a block and using e.g. a
		door, so this is just a wrapper function for better code readability.
		"""
		return self.placeBlock(targetPosition, jumpOnUse)


	def tileGrassAndPlantSeeds(self, targetPosition, hoeSlot, seedsSlot):
		"""
		You can call this function repeatedly (in a loop) to tile grass and
		plant a seed on the targetPosition.
		It will return True if the agent is in the process of tiling grass and
		planting seeds, and it will return False if it has succeeded in doing
		so, or if it has run out of seeds.

		TODO: Improve return state
		"""

		# Check if we have enough seeds left
		if not self.inventoryHandler.hasItemInHotbar(SEEDS):
			return False

		# Check distance to block (for vision range check)
		relTargetPos = np.floor(targetPosition).astype(int) - self.intPlayerPos
		x, y, z = relTargetPos

		if not self.visionHandler.inVisionRange(x, y, z):
			# Not in vision range, move/navigate towards it
			# TODO: Use navigation
			self.controller.lookAt(targetPosition)
			self.controller.moveForward()
			return True

		# Check if the target position is grass, or farmland
		visionBlockType = self.visionHandler.getBlockAtRelPos(x, y, z)

		# Return True even if we have just placed the seeds, since theres a 1%
		# chance that it fails to place the seeds...
		if visionBlockType == BLOCK_FARM_LAND:
			self.controller.selectHotbar(seedsSlot)
			placedSeeds = self.useItem(targetPosition)

			# Only if the block above the targetPosition is wheat, can we be
			# sure that we have successfully planted seeds
			return not self.visionHandler.isBlock(x, y + 1, z, BLOCK_WHEAT)
		elif visionBlockType == BLOCK_GRASS:
			self.controller.selectHotbar(hoeSlot)
			self.placeBlock(targetPosition)
			return True
		else:
			print "No farmland or grass at targetPosition {}! Rel = {}".format(
				targetPosition, relTargetPos)
			print "Expected grass or farmland, got \"{}\"...".format(
				self.visionHandler.getBlockAtRelPos(x, y, z))
			return False


	def craft(self, item):
		self.agent.sendCommand("craft {}".format(item))


	def collectDrops(self, dropType):
		"""
		Collects dropped items by walking over to them. This function should be
		called in a loop, just like destroyBlock(). It returns True for as long
		as there are drops to collect, and False when there are no more drops.
		"""

		# Check if we can collect some drops, and pick them up...
		dropPositions = self.entitiesHandler.getEntityPositions(dropType)

		if len(dropPositions) != 0:
			# TODO: Use navigation...
			self.controller.lookAt(dropPositions[0])
			self.controller.moveForward()
			return True
		else:
			return False
