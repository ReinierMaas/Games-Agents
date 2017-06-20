# Code for filtering non-visible blocks based on a given observation and small tests

import MalmoPython
import numpy as np

from util import *

################################################################################
# Configuration for observation cube and vision handling
################################################################################

CUBE_OBS = "vision_cube"		# Name that will be used in XML/JSON
CUBE_SIZE = 1 					# Number of visible blocks in 1 direction

ENTITIES_OBS = "entities"		# Name that will be used in XML/JSON
ENTITIES_RANGE = 25				# Number of blocks in 1 direction that we can
								# observe entities from



################################################################################
# Main Vision handling class (blocks)
################################################################################

class VisionHandler(object):
	"""
	Class for handling vision through the use of observation cubes, cube size
	is in 1 direction. Use this class to help the agent "see".
	"""
	def __init__(self, size):
		super(VisionHandler, self).__init__()
		self.size = size

		# Since real cube size is for both directions, we also do +1 for player
		self.realSize = size * 2 + 1
		self.numElements = self.realSize**3
		self.center = size
		self.matrix = np.zeros((self.realSize, self.realSize, self.realSize),
			dtype="|S25")

		self.__setupVisibilityMatrix()
		self.__setupVisibleBlockList()


	def __repr__(self):
		return "{}".format(self.matrix)


	def updateFromObservation(self, observation):
		""" Converts the 1D list of vision cube blocks into our 3D matrix. """

		# Sanity checks, just in case
		if CUBE_OBS not in observation:
			raise ValueError("cube observation key not in observation JSON!")

		cubeObservation = observation[CUBE_OBS]

		if len(cubeObservation) != self.numElements:
			raise ValueError("cube observation uses different cube size!")

		# Directly copy over the list to a numpy matrix, reset the shape, and
		# swap the y and z axes (previous index / Malmo uses x, z, y)
		# 25 characters should be enough for block names...
		temp = np.array(cubeObservation, dtype="|S25")
		temp = np.reshape(temp, (self.realSize, self.realSize, self.realSize))
		self.matrix = np.swapaxes(temp, 1, 2)
		self.__filterOccluded()


	def inVisionRange(self, relX, relY, relZ):
		""" Returns True/False if the given relative coords are within vision range. """
		return self.areValidRelCoords(relX, relY, relZ)


	def areValidRelCoords(self, relX, relY, relZ):
		""" Returns True/False if the given relative coords are valid. """
		if relX < -self.size or relX > self.size:
			return False

		if relY < -self.size or relY > self.size:
			return False

		if relZ < -self.size or relZ > self.size:
			return False

		return True


	def getBlockAtRelPos(self, relX, relY, relZ):
		"""
		Returns the block at the given x, y, z position relative to the player.
		Returns empty string if -size > x, y, z or x, y, z > size (out of bounds).
		This also corresponds to "we don't know whats there".
		"""
		if self.areValidRelCoords(relX, relY, relZ):
			return self.matrix[self.center + relY, self.center + relX, self.center + relZ]
		else:
			return ""


	def isBlock(self, relX, relY, relZ, blockName):
		""" Returns True/False if the given block is at the given relative position. """
		return self.getBlockAtRelPos(relX, relY, relZ) == blockName



	def findBlocks(self, blockName):
		"""
		Returns a np array of np.array([x, y, z]) coordinates, where the given
		block is. An empty list is returned if the block cant be found. The
		returned list is sorted by distance from the player, so the closest
		blocks will be returned first. This list returns coordinates relative
		to the player position.
		"""
		coordinates = []
		distances = []
		playerPos = np.array([0.0, 0.0, 0.0])

		# Find the block we're looking for
		for block in self.visibleBlocks:
			x, y, z = block

			if self.isBlock(x, y, z, blockName):
				coordinates.append(np.array([x, y, z]))
				distances.append(getVectorDistance(block, playerPos))

		# Now we sort the blocks based on distance from the player
		coordinates = np.array(coordinates)
		distances = np.array(distances)
		sortedIndices = distances.argsort()
		return coordinates[sortedIndices]



	def getWalkableBlocks(self):
		""" Returns a list of all [x, y, z] blocks that the player can stand on. """

		walkableBlocks = []

		for block in self.visibleBlocks:
			x, y, z = block

			if (self.getBlockAtRelPos(x, y, z) not in UNWALKABLE_BLOCKS and \
			self.isBlock(x, y + 1, z, "air") and self.isBlock(x, y + 2, z, "air")):

				walkableBlocks.append(block)

		return walkableBlocks



	def getUniqueVisibleBlocks(self):
		""" Returns a list of unique blocktypes visible. """

		uniqueBlocks = []

		for block in self.visibleBlocks:
			x, y, z = block
			blockType = self.getBlockAtRelPos(x, y, z)

			if blockType != "" and blockType not in uniqueBlocks:
				uniqueBlocks.append(blockType)

		return uniqueBlocks



	def __setupVisibilityMatrix(self):
		self.visible = np.zeros((self.realSize, self.realSize, self.realSize), dtype=bool)


	def __fixDefaultVisibility(self):
		""" We can always "see" the 2 blocks where the player is standing """
		self.visible[self.center, self.center, self.center] = True
		self.visible[self.center + 1, self.center, self.center] = True


	def isVisible(self, relX, relY, relZ):
		""" Returns True/False if the given relative x, y, z block is visible. """
		return self.visible[self.center + relY, self.center + relX, self.center + relZ]


	def __setVisible(self, relX, relY, relZ):
		""" Sets the given relative x, y, z block to visible """
		self.visible[self.center + relY, self.center + relX, self.center + relZ] = True


	def __setInvisible(self, relX, relY, relZ):
		""" Sets the block at relative x, y, z coordinates to empty string. """
		self.visible[self.center + relY, self.center + relX, self.center + relZ] = False


	def __applyVisibility(self):
		""" Applies the visiblity matrix to the observation matrix. """
		for x in range(-self.size, self.size + 1):
			for y in range(-self.size, self.size + 1):
				for z in range(-self.size, self.size + 1):
					if not self.isVisible(x, y, z):
						self.matrix[self.center + y, self.center + x, self.center + z] = ""

		self.__updateVisibleBlockList()


	def __setupVisibleBlockList(self):
		"""
		Used to setup the list of visible blocks that can be used by FOV
		filtering and raytracing.
		"""

		self.visibleBlocks = []


	def __addVisibleBlock(self, block):
		self.visibleBlocks.append(block)


	def __updateVisibleBlockList(self):
		""" Updates the list of visible blocks """
		self.__setupVisibleBlockList()

		for x in range(-self.size, self.size + 1):
			for y in range(-self.size, self.size + 1):
				for z in range(-self.size, self.size + 1):
					if self.isVisible(x, y, z):
						self.__addVisibleBlock(np.array([x, y, z]))



	def __filterCoarse(self):
		"""
		Determines the visibility matrix by doing a fast, coarse filtering of
		non-visible blocks, by looking at transparant blocks around the player
		and expanding outwards. This is a helper function and shouldnt be used
		directly outside this class. Ensure the self.visible matrix is available
		and initialized properly (aka, everything to False)...
		"""

		# First we filter out all blocks that are not adjacent to a transparant
		# block, since they will not be visible anyway. We do this by starting
		# from the players eyes, and gradually marking visible/unvisible blocks
		# outwards.

		# The blocks where the player is standing is always visible of course...
		# Unless we are suffocating... in which case we're fucked...
		# Future TODO: Figure something out or not, I dont care
		if self.getBlockAtRelPos(0, 0, 0) not in TRANSPARANT_BLOCKS and \
						self.getBlockAtRelPos(0, 1, 0) not in TRANSPARANT_BLOCKS:

			# Yup, we're suffocating... FUCK FUCK FUCK
			for i in range(42):
				print "I CAN'T BREEEAATTHEEE!! HELP ME I'M FUCKING SUFFOCATING!!!"

		self.__fixDefaultVisibility()

		# We basically expand our search for visible blocks outward from where
		# the player is standing, and check adjacant blocks to see if they are
		# visible.
		# There are edge cases in which a block is not marked visible because
		# none of its neighbors have been marked as such, but they are in fact
		# potentially visible since its neighbors will be marked visible later
		# on. We can either fix this by doing multiple passes (easy), or by
		# changing the loops to work in an actual, outwards spiral (harder)...
		# Future TODO: Improve upon multiple passes method with something smarter
		iterations = 0

		while True:
			changedSomething = False

			for x in range(0, self.size + 1) + range(-1, -self.size - 1, -1):
				for y in range(0, self.size + 1) + range(-1, -self.size - 1, -1):
					for z in range(0, self.size + 1) + range(-1, -self.size - 1, -1):

						# If this block is already visible, skip it
						if self.isVisible(x, y, z):
							continue

						# Check 6 surrounding blocks if they're visible, first
						# we check left and right blocks (x direction)
						if x + 1 < self.size and self.isVisible(x + 1, y, z) and \
						self.getBlockAtRelPos(x + 1, y, z) in TRANSPARANT_BLOCKS:

							self.__setVisible(x, y, z)
							changedSomething = True
							continue

						if x - 1 > -self.size and self.isVisible(x - 1, y, z) and \
						self.getBlockAtRelPos(x - 1, y, z) in TRANSPARANT_BLOCKS:

							self.__setVisible(x, y, z)
							changedSomething = True
							continue

						# Then we check above and below blocks (y direction)
						if y + 1 < self.size and self.isVisible(x, y + 1, z) and \
						self.getBlockAtRelPos(x, y + 1, z) in TRANSPARANT_BLOCKS:

							self.__setVisible(x, y, z)
							changedSomething = True
							continue

						if y - 1 > -self.size and self.isVisible(x, y - 1, z) and \
						self.getBlockAtRelPos(x, y - 1, z) in TRANSPARANT_BLOCKS:

							self.__setVisible(x, y, z)
							changedSomething = True
							continue

						# And finally check front and back blocks (z direction)
						if z + 1 < self.size and self.isVisible(x, y, z + 1) and \
						self.getBlockAtRelPos(x, y, z + 1) in TRANSPARANT_BLOCKS:

							self.__setVisible(x, y, z)
							changedSomething = True
							continue

						if z - 1 > -self.size and self.isVisible(x, y, z - 1) and \
						self.getBlockAtRelPos(x, y, z - 1) in TRANSPARANT_BLOCKS:

							self.__setVisible(x, y, z)
							changedSomething = True
							continue

						# If no nieighbors are visible, this block is likely not
						# visible either.
						self.__setInvisible(x, y, z)

			iterations += 1

			if not changedSomething:
				break



	def __filterOccluded(self):
		""" Filters out all occluded blocks that the agent cannot see. """

		# Setup the visibility matrix, and do coarse filtering
		self.__setupVisibilityMatrix()
		self.__setupVisibleBlockList()
		self.__filterCoarse()
		self.__applyVisibility()




################################################################################
# Secondary Vision handling class (entities)
################################################################################

class EntitiesHandler(object):
	"""	Class for handling vision for entities. """
	def __init__(self):
		super(EntitiesHandler, self).__init__()
		self.entities = None


	def __repr__(self):
		return "{}".format(self.entities)


	def updateFromObservation(self, observation):
		""" Updates the visible entities from the given observation """

		self.entities = observation.get(ENTITIES_OBS)	# Defaults to None
		self.playerPos = getPlayerPos(observation, False)


	def getEntityPositions(self, entityToFind):
		"""
		Returns a numpy array of numpy arrays where the requested entity/entities
		are, or else an empty numpy array if no entities can be found in the list.
		The array will be sorted based on the distance to the entities (closest
		first in the list).
		"""
		positionsFound = []
		distances = []

		if self.entities is None:
			return np.array(positionsFound)

		for entity in self.entities:
			if entity[u"name"] == entityToFind:
				x, y, z = entity[u"x"], entity[u"y"], entity[u"z"]
				xyz = np.array([x, y, z])
				positionsFound.append(xyz)
				distances.append(distanceH(self.playerPos, xyz))

		# Now we sort the list based on the distance to the entity
		positionsFound = np.array(positionsFound)
		distances = np.array(distances)
		sortedIndices = distances.argsort()
		return positionsFound[sortedIndices]


	def getEntityCounts(self, entityToFind=None):
		"""
		Returns a dictionairy for every entity within the visible range with
		the amount of that entity that (e.g. : {"log": 2, "player": 1}).
		Optionally, entityToFind can be given, and an integer is returned that
		indicates how many of that entity is visible (0 if not).
		"""
		if self.entities is None:
			return 0 if entityToFind is not None else {}

		counts = {}

		for entity in self.entities:
			name = entity[u"name"]
			counts[name] = counts.get(name, 0) + entity.get(u"quantity", 0)

		if entityToFind is not None:
			return counts.get(entityToFind, 0)

		return counts




