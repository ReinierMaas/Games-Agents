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
		print "self.playerPos = {}, self.intPlayerPos = {}".format(
			self.playerPos, self.intPlayerPos)


	def findWood(self):
		""" See visionHandler.findBlocks function, returns coordinates of logs. """
		return self.visionHandler.findBlocks(BLOCK_WOOD)


	def chopTree(self, lineOfSightDict, treePosition = None):
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

		# Find all the wood in our vicinity
		woodPositions = self.findWood()

		if treePosition is None:
			print "GIMME TREE"

			if woodPositions != []:
				treePosition = woodPositions[0] + self.intPlayerPos
			else:
				# TODO: Look for a tree in the navigation/waypoint stuff...
				print "Not implemented yet!"
				return False

		print "woodPositions = {}".format(woodPositions)

		# Figure out if tree is in view distance, and thus figure out if we're
		# able to get the rest of the logs of the tree.
		distanceToTree = distanceH(self.playerPos, treePosition)
		movementSpeed = distanceToTree / 3.0
		treeLogPositions = [treePosition]
		viewDistance = sqrt(3 * (CUBE_SIZE + 1)**2)

		if getVectorDistance(self.intPlayerPos, treePosition) <= viewDistance:
			treeX, treeY, treeZ = treePosition

			# Tree is visible, get rest of the log blocks of it
			for logBlock in woodPositions:
				blockX, blockY, blockZ = self.intPlayerPos + logBlock

				if treeX == blockX and treeZ == blockZ:
					treeLogPositions.append(logBlock)
		else:
			# Tree is outside our view distance, move towards it!
			# TODO: Use proper navigation
			print "Tree is outside view distance, moving towards it!"
			self.controller.lookAt(treePosition)
			self.controller.moveForward()
			return True

		print "Logs of tree = {}".format(treeLogPositions)

		losBlock = getLineOfSightBlock(lineOfSightDict)
		inRange = lineOfSightDict[u"inRange"]
		losBlockIsWood = lineOfSightDict[u"type"] == BLOCK_WOOD
		print "LOS Dict = {}".format(lineOfSightDict)
		print "losBlock = {}, inRange = {}, isWood = {}".format(losBlock,
			inRange, losBlockIsWood)

		# Check if we have targeted one of the logs of the tree
		targetedOneBlock = False

		for logBlock in treeLogPositions:
			if (losBlock == logBlock).all():
				# Yes, we have it targeted, check if its in range and if its wood
				print "Yes, we have block {} targeted!".format(losBlock)
				targetedOneBlock = True

				if inRange:
					if losBlockIsWood:
						# Stop moving and chop it down
						print "Looking at target tree, chopping it down!"
						self.controller.stopMoving()
						# self.controller.lookAt(treePosition)
						self.controller.setAttackMode(True)
						return True
					else:
						# In range but not wood, so that means it has been
						# replaced by something else, since our vision says
						# that it should be a log block
						print "Expected log at {} but got {}".format(
							logBlock, lineOfSightDict[u"type"])
						continue
				else:
					# Not in range, move towards it
					# TODO: Use real navigation...
					print "Tree not in range, moving towards it..."
					self.controller.setAttackMode(False)
					self.controller.lookAt(logBlock)
					self.controller.moveForward(movementSpeed)
					return True

		if not targetedOneBlock:
			print "We failed to target the tree, aiming for it now..."
			self.controller.setAttackMode(False)
			difference = treePosition - losBlock
			self.controller.lookAt(treePosition + difference * 0.5)
			# self.controller.lookAt(treePosition)
			return True

		# We've gotten all of the blocks of the tree, tree is down!
		print "Got all logs of this tree!"

		# TODO: Check log drops and pick them up

