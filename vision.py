# Code for filtering non-visible blocks based on a given observation and small tests

import MalmoPython
import os
import random
import sys
import time
import json
import copy
import errno
from math import ceil, radians, degrees, acos, tan, sqrt, fsum
import xml.etree.ElementTree
import numpy as np

# Configuration for observation cube, with name in XML/JSON and size in 1 direction
CUBE_OBS = "cube10"
CUBE_SIZE = 2

PLAYER_EYES = 1.625  			# Player's eyes are at y = 1.625 blocks high
PLAYER_EYES_CROUCHING = 1.5		# Player's eyes are at y = 1.5 when crouching
FOV = 70						# Default Field of View for Minecraft


TRANSPARANT_BLOCKS = ["glass", "air", "sapling", "cobweb", "flower", "mushroom",
	"torch", "ladder", "fence", "iron_bars", "glass_pane", "vines", "lily_pad",
	"sign", "item_frame", "flower_pot", "skull", "armor_stand", "banner", "tall_grass",
	"lever", "pressure_plate", "redstone_torch", "button", "trapdoor", "tripwire",
	"tripwire_hook", "redstone", "rail", "beacon", "cauldron", "brewing_stand"]

BLOCK_WOOD = "log"


# Note for future use about pitch and yaw
# Pitch = angle in the range (-180, 180] (left/right rotate)
# 	-180 or 180 		facing north (towards negative z)
# 	90 					facing west  (towards negative x)
# 	0					facing south (towards positive z)
# 	-90					facing east  (towards positive x)
# Yaw = angle in the range [-90, 90] (up/down)
#	0 					horizontal, parallel to the ground
# 	-90					vertical, looking to the sky
#	90					vertical, looking to the ground


def getVectorLength(vector):
	""" Returns the length of the vector. """

	# fsum is more accurate and uses Kahan summation along with IEEE-754 fp stuff
	return sqrt(fsum([element * element for element in vector]))

def getNormalizedVector(vector):
	""" Returns the normalized vector. """
	length = getVectorLength(vector)

	if length != 0.0:
		return vector / length
	else:
		return vector


class Ray(object):
	"""
	Helper class to handle Rays that are used for ray-tracing with minecraft
	blocks, to perform realistic visibility tests.
	"""

	# Some constants to use for ray-tracing
	MAX_T = 1e34
	EPSILON_T = 0.0001

	def __init__(self, origin, direction):
		"""
		Origin and direction should be 3D numpy vectors, and direction must be
		normalized.
		"""
		super(Ray, self).__init__()
		self.origin = origin
		self.direction = direction

	def getOrigin(self):
		return self.origin

	def getDirection(self):
		return self.direction

	def getPosition(self, t):
		""" Returns the position of the ray for the given t value. """
		return self.origin + t * self.direction


class Triangle(object):
	"""
	Helper class to handle Triangles that are used for ray-tracing with minecraft
	blocks, to perform realistic visibility tests.
	"""
	INTERSECTION_EPSILON = 0.000001

	def __init__(self, normal, vertices):
		"""
		Please use 3D numpy vectors for every vector. Note that vertices should
		be a list or numpy array of three, 3D numpy vectors, and normal must be
		a normalized vector.
		"""
		super(Triangle, self).__init__()
		self.normal = normal
		self.vertices = np.copy(vertices)
		self.edge1 = vertices[1] - vertices[0]
		self.edge2 = vertices[2] - vertices[0]


	def intersect(self, ray):
		"""
		Checks if the given ray intersects this triangle, and if so, returns the
		corresponding t value. If not, None is returned.
		"""

		# Calculate if the ray can actually intersect the triangle (dot product)
		p = np.cross(ray.getDirection(), self.edge2)
		det = np.dot(self.edge1, p)

		if det > -INTERSECTION_EPSILON and det < INTERSECTION_EPSILON:
			return None

		# Possible intersection, calculate bary-centric coordinates
		inverseDet = 1.0 / det
		temp = ray.getOrigin() - self.vertices[0]
		u = np.dot(temp, p) * inverseDet

		if u < 0.0 or u > 1.0:
			return None

		q = np.cross(temp, self.edge1)
		v = np.dot(ray.getDirection(), q) * inverseDet

		if v < 0.0 or u + v > 1.0:
			return None

		# Calculate t value since we have a valid intersection
		t = np.dot(edge2, q) * inverseDet
		return t


class Block(object):
	"""
	Helper class to handle Blocks that are used for ray-tracing with minecraft
	blocks, to perform realistic visibility tests.
	"""
	def __init__(self, relX, relY, relZ):
		"""
		Initializes the block with the relative x, y, z coordinates to the
		player, and constructs 6 triangles for the 3 closest perpendicular faces.
		"""
		self.x = relX
		self.y = relY
		self.z = relZ

		# Get all corners of this block, labeled clockwise...
		self.corners = [
			np.array([relX + 1, relY + 1, relZ], dtype=float),	# "Top" corners
			np.array([relX + 1, relY + 1, relZ + 1], dtype=float),
			np.array([relX, relY + 1, relZ + 1],dtype=float),
			np.array([relX, relY + 1, relZ], dtype=float),

			np.array([relX + 1, relY, relZ], dtype=float),		# "Bottom" corners
			np.array([relX + 1, relY, relZ + 1], dtype=float),
			np.array([relX, relY, relZ + 1], dtype=float),
			np.array([relX, relY, relZ], dtype=float),
		]

		# TODO: Double check normals/vertices again... (seem ok now...) (check again)
		# Get closest and furthest face orthogonal to x direction in z, y plane
		normalX1 = getNormalizedVector(np.array([-relX, relY, relZ]))
		normalX2 = getNormalizedVector(np.array([relX, relY, relZ]))

		# Create 4 triangles for those 2 faces
		faceX11 = Triangle(normalX1, [self.corners[3], self.corners[2], self.corners[6]])
		faceX12 = Triangle(normalX1, [self.corners[3], self.corners[6], self.corners[7]])
		faceX21 = Triangle(normalX2, [self.corners[0], self.corners[4], self.corners[5]])
		faceX22 = Triangle(normalX2, [self.corners[0], self.corners[5], self.corners[1]])

		# Get lowest and highest face orthogonal to y direction in x, z plane
		normalY1 = getNormalizedVector(np.array([relX, -relY, relZ]))
		normalY2 = getNormalizedVector(np.array([relX, relY, relZ]))

		faceY11 = Triangle(normalY1, [self.corners[4], self.corners[5], self.corners[6]])
		faceY12 = Triangle(normalY1, [self.corners[4], self.corners[6], self.corners[7]])
		faceY21 = Triangle(normalY2, [self.corners[0], self.corners[1], self.corners[2]])
		faceY22 = Triangle(normalY2, [self.corners[0], self.corners[2], self.corners[3]])

		# Get closest and furthest face orthogonal to z direction in x, y plane
		normalZ1 = getNormalizedVector(np.array([relX, relY, -relZ]))
		normalZ2 = getNormalizedVector(np.array([relX, relY, relZ]))

		faceZ11 = Triangle(normalZ1, [self.corners[1], self.corners[5], self.corners[6]])
		faceZ12 = Triangle(normalZ1, [self.corners[1], self.corners[6], self.corners[2]])
		faceZ21 = Triangle(normalZ2, [self.corners[0], self.corners[3], self.corners[7]])
		faceZ22 = Triangle(normalZ2, [self.corners[0], self.corners[7], self.corners[4]])

		# Collect all of the triangles
		self.triangles = [faceX11, faceX12, faceX21, faceX22,
			faceY11, faceY12, faceY21, faceY22,
			faceZ11, faceZ12, faceZ21, faceZ22]


	def getX(self):
		return self.x

	def getY(self):
		return self.y

	def getZ(self):
		return self.z

	def getCorners(self):
		return self.corners


	def intersect(self, ray, doEarlyOut = True):
		"""
		Returns t value if ray intersects the block, else None. Optionally,
		doEarlyOut can be set to False to return the lowest valid t value, if any.
		"""

		lowestT = 1e38

		for triangle in self.triangles:
			t = triangle.intersect(ray)

			if doEarlyOut:
				if t > 0.0 and t is not None:
					return t
			else:
				if t > 0.0 and t < lowestT:
					lowestT = t

		return lowestT if lowestT is not 1e38 else None



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

		self._setupVisibilityMatrix()
		self._setupVisibleBlockList()


	def updateFromObservation(self, cubeObservation):
		"""
		Converts the 1D list of blocks into our 3D matrix. Don't forget to call
		filterOccluded() afterwards!
		"""

		# Sanity check, just in case
		if len(cubeObservation) != self.numElements:
			raise ValueError("cube observation uses different cube size!")

		# Directly copy over the list to a numpy matrix, reset the shape, and
		# swap the y and z axes (previous index / Malmo uses x, z, y)
		# 25 characters should be enough for block names...
		temp = np.array(cubeObservation, dtype="|S25")
		temp = np.reshape(temp, (self.realSize, self.realSize, self.realSize))
		self.matrix = np.swapaxes(temp, 1, 2)


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
			return self.matrix[self.center + relX, self.center + relY, self.center + relZ]
		else:
			return ""

	def isBlock(self, relX, relY, relZ, block):
		""" Returns True/False if the given block is at the given relative position. """
		return self.getBlockAtRelPos(relX, relY, relZ) == block

	def findBlocks(self, block):
		"""
		Returns a list of [x, y, z] coordinates as a list of numpy arrays, where
		the given block is. An empty list is returned if the block cant be found.
		"""
		coordinates = []

		for block in self.visibleBlocks:
			x, y, z = block.getX(), block.getY(), block.getZ()

			if isBlock(x, y, z, block):
				coordinates.append(np.array([x, y, z]))

		return coordinates

	def findWood(self, block):
		""" See findBlocks function, returns coordinates of wood/log. """
		return self.findBlocks(BLOCK_WOOD)


	def _setupVisibilityMatrix(self):
		self.visible = np.zeros((self.realSize, self.realSize, self.realSize), dtype=bool)

	def _fixDefaultVisibility(self):
		""" We can always "see" the 2 blocks where the player is standing """
		self.visible[self.center, self.center, self.center] = True
		self.visible[self.center, self.center + 1, self.center] = True


	def isVisible(self, relX, relY, relZ):
		""" Returns True/False if the given relative x, y, z block is visible. """
		return self.visible[self.center + relX, self.center + relY, self.center + relZ]

	def setVisible(self, relX, relY, relZ):
		""" Sets the given relative x, y, z block to visible """
		self.visible[self.center + relX, self.center + relY, self.center + relZ] = True

	def setInvisible(self, relX, relY, relZ):
		""" Sets the block at relative x, y, z coordinates to empty string. """
		self.visible[self.center + relX, self.center + relY, self.center + relZ] = False


	def applyVisibility(self):
		""" Applies the visiblity matrix to the observation matrix. """
		for x in range(-self.size, self.size + 1):
			for y in range(-self.size, self.size + 1):
				for z in range(-self.size, self.size + 1):
					if not self.isVisible(x, y, z):
						self.matrix[self.center + x, self.center + y, self.center + z] = ""

		self.updateVisibleBlockList()


	def _setupVisibleBlockList(self):
		"""
		Used to setup the list of visible blocks that can be used by FOV
		filtering and raytracing.
		"""

		self.visibleBlocks = []

	def addVisibleBlock(self, block):
		self.visibleBlocks.append(block)

	def updateVisibleBlockList(self):
		""" Updates the list of visible blocks """
		self._setupVisibleBlockList()

		for x in range(-self.size, self.size + 1):
			for y in range(-self.size, self.size + 1):
				for z in range(-self.size, self.size + 1):
					if self.isVisible(x, y, z):
						self.addVisibleBlock(Block(x, y, z))


	def _filterCoarse(self):
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

		self._fixDefaultVisibility()

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

							self.setVisible(x, y, z)
							changedSomething = True
							continue

						if x - 1 > -self.size and self.isVisible(x - 1, y, z) and \
						self.getBlockAtRelPos(x - 1, y, z) in TRANSPARANT_BLOCKS:

							self.setVisible(x, y, z)
							changedSomething = True
							continue

						# Then we check above and below blocks (y direction)
						if y + 1 < self.size and self.isVisible(x, y + 1, z) and \
						self.getBlockAtRelPos(x, y + 1, z) in TRANSPARANT_BLOCKS:

							self.setVisible(x, y, z)
							changedSomething = True
							continue

						if y - 1 > -self.size and self.isVisible(x, y - 1, z) and \
						self.getBlockAtRelPos(x, y - 1, z) in TRANSPARANT_BLOCKS:

							self.setVisible(x, y, z)
							changedSomething = True
							continue

						# And finally check front and back blocks (z direction)
						if z + 1 < self.size and self.isVisible(x, y, z + 1) and \
						self.getBlockAtRelPos(x, y, z + 1) in TRANSPARANT_BLOCKS:

							self.setVisible(x, y, z)
							changedSomething = True
							continue

						if z - 1 > -self.size and self.isVisible(x, y, z - 1) and \
						self.getBlockAtRelPos(x, y, z - 1) in TRANSPARANT_BLOCKS:

							self.setVisible(x, y, z)
							changedSomething = True
							continue

						# If no nieighbors are visible, this block is likely not
						# visible either.
						self.setInvisible(x, y, z)

			iterations += 1

			if not changedSomething:
				break


	def _filterFOV(self, lookAt):
		""" Filters out all non-visible blocks that the agent cannot see """

		# Convert all currently visible blocks to blocks of triangles. Also, we
		# do a simple angle test with blocks that are absolutely out of view

		# TODO: Fix fov calculation into correct one that minecraft uses...
		fov = radians(FOV)

		# print "lookAt = {}, fov = {}\n".format(lookAt, fov)
		print "coarse filtered matrix = \n{}".format(self.matrix)

		for block in self.visibleBlocks:
			x, y, z = block.getX(), block.getY(), block.getZ()

			# Skip all non-visible blocks
			if self.isVisible(x, y, z):
				# Check dot product visibility for visible blocks, aka
				# angle test for every corner of the block. If one of
				# the corners is visible, then the block is considered
				# visible as well.
				cornerVisible = False
				corners = block.getCorners()

				for i in range(len(corners)):
					cornerDir = getNormalizedVector(corners[i])
					angle = acos(np.dot(cornerDir, lookAt))
					# print "corner {}, angle = {}".format(i, angle)

					if angle >= -fov and angle <= fov:
						cornerVisible = True
						# print "\tblock is visible!"
						break

				if not cornerVisible:
					# print "\t block is NOT visible!"
					self.setInvisible(x, y, z)

		self._fixDefaultVisibility()


	def _filterRayTraced(self, lookAt, playerIsCrouching = False):
		"""
		Filters occluded blocks by using ray-tracing of the visible blocks...
		TODO: FINISH THIS AND FIX IT
		"""

		# Now we can ray-trace all the blocks... First, we setup a 2D grid of
		# rays that we will shoot from the players eyes...
		numX = 160
		numY = 90
		distance = 0.1

		# Calculate some FOV bullshit
		aspectRatio = numX * 1.0 / numY
		fov = radians(FOV) / 2.0
		ratioFov = tan(fov)

		# Get the origin of the camera (aka the eyes)
		origin = np.array([0, PLAYER_EYES_CROUCHING if playerIsCrouching else PLAYER_EYES, 0])

		# Get left and up directions of the image plane
		left = getNormalizedVector(np.cross(lookAt + np.array([0, 0.1, 0]), lookAt))
		up = getNormalizedVector(np.cross(lookAt, left))
		left = getNormalizedVector(np.cross(up, lookAt))

		# Get corners of the view plane and plane vectors
		center = origin + lookAt * distance
		p0 = center - left + up
		p1 = center + left + up
		p2 = center - left - up
		right = p1 - p0
		up = p2 - p0

		# Make a copy of the visiblity matrix, since we need our own
		visibleBackup = np.copy(self.visible)

		# The visibility matrix is reset because we only mark the visible blocks
		# as visible, and dont filter out visible blocks
		self._setupVisibilityMatrix()

		# Generate all the rays and trace them
		for y in range(numY):
			# Make sure vStep is in the range [-1.0, 1.0]
			vStep = y * 2.0 / numY - 1.0

			for x in range(numX):
				# Make sure uStep is also in the same range
				uStep = x * 2.0 / numX - 1.0

				# Calculate ray direction vector based on x and y coords
				rayDirection = lookAt + right * ratioFov * aspectRatio * uStep + \
					up * ratioFov * vStep
				ray = Ray(origin, getNormalizedVector(rayDirection))

				# Trace new ray for intersection, test against all visible blocks...
				intersectedBlocks = []
				intersectedBlockTypes = []
				intersectionT = []

				for block in self.visibleBlocks:
					# Don't do early out, since we need the closest t for sorting...
					t = block.intersect(ray, False)

					if t is not None:
						intersectedBlocks.append(block)
						x, y, z = block.getX(), block.getY(), block.getZ()
						intersectedBlockTypes.append(self.getBlockAtRelPos(x, y, z))
						intersectionT.append(t)

				# Check if this ray hit anything and update visibility
				if intersectedBlocks is not []:
					# Now we need to order the intersected blocks based on their
					# intersected t values, so we can clip non-visible blocks...
					order = np.array(intersectionT).argsort()
					orderedBlocks = np.array(intersectedBlocks)[order]
					orderedTypes = np.array(intersectedBlockTypes)[order]

					hitNonTransparantBlock = False

					# We can only see transparant blocks until we hit the first
					# non-transparant block, all the others are likely occluded
					# for this pixel
					for block, blockType in zip(orderedBlocks, orderedTypes):
						x, y, z = block.getX(), block.getY(), block.getZ()

						if blockType in TRANSPARANT_BLOCKS:
							if not hitNonTransparantBlock:
								self.setVisible(x, y, z)
						else:
							if not hitNonTransparantBlock:
								hitNonTransparantBlock = True
								self.setVisible(x, y, z)

		self._fixDefaultVisibility()


	def filterOccluded(self, lookAt, playerIsCrouching = False):
		""" Filters out all occluded blocks that the agent cannot see. """

		lookAt = getNormalizedVector(lookAt)

		# First we setup the visibility matrix, and do coarse filtering
		self._setupVisibilityMatrix()
		self._setupVisibleBlockList()	# Used for _filterFOV and _filterRayTraced
		self._filterCoarse()
		self.applyVisibility()

		# Then we do more advanced filtering based on the FOV of the player
		# oldVisible = np.copy(self.visible)
		# self._filterFOV(lookAt)
		# difference = (oldVisible != self.visible)
		# print "filterFOV changed something = {}".format(difference.any())
		# self.applyVisibility()

		# Finally, we can do ray-tracing to determine occluded blocks...
		# oldVisible = np.copy(self.visible)
		# self._filterRayTraced(lookAt, playerIsCrouching)
		# difference = (oldVisible != self.visible)
		# print "filterRayTraced changed something = {}".format(difference.any())
		# self.applyVisibility()

		# print self.matrix



def getMissionXML():
	""" Generates mission XML with flat world and 1 crappy tree. """
	return """<?xml version="1.0" encoding="UTF-8" ?>
		<Mission xmlns="http://ProjectMalmo.microsoft.com" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
			<About>
				<Summary>Test filtering of visible blocks</Summary>
			</About>

			<ServerSection>
				<ServerInitialConditions>
					<Time>
						<StartTime>1000</StartTime>
						<AllowPassageOfTime>true</AllowPassageOfTime>
					</Time>

					<Weather>clear</Weather>
				</ServerInitialConditions>

				<ServerHandlers>
					<FlatWorldGenerator generatorString="3;7,5*3,2;1;" forceReset="true" />

					<DrawingDecorator>
						<DrawSphere x="-5" y="11" z="0" radius="3" type="leaves" />
						<DrawLine x1="-5" y1="7" z1="0" x2="-5" y2="11" z2="0" type="log" />
						<DrawLine x1="-6" y1="7" z1="-1" x2="-6" y2="7" z2="1" type="stone" />
						<DrawLine x1="-6" y1="8" z1="-1" x2="-6" y2="8" z2="1" type="glass" />
					</DrawingDecorator>

					<ServerQuitWhenAnyAgentFinishes />
					<ServerQuitFromTimeUp timeLimitMs="600000" description="Ran out of time." />
				</ServerHandlers>
			</ServerSection>

			<AgentSection mode="Creative">
				<Name>YourMom</Name>
				<AgentStart>
					<Placement x="0.5" y="7.0" z="0.5" yaw="90" />
				</AgentStart>

				<AgentHandlers>
					<ContinuousMovementCommands />
					<InventoryCommands />
					<ObservationFromFullStats />
					<ObservationFromRay />
					<ObservationFromHotBar />
					<ObservationFromGrid>
						<Grid name="{0}">
							<min x="-{1}" y="-{1}" z="-{1}"/>
							<max x="{1}" y="{1}" z="{1}"/>
						</Grid>

						<Grid name="floor3x3">
							<min x="-1" y="-1" z="-1"/>
							<max x="1" y="-1" z="1"/>
						</Grid>
					</ObservationFromGrid>
				</AgentHandlers>
			</AgentSection>
		</Mission>""".format(CUBE_OBS, CUBE_SIZE)


# Create a simple flatworld mission and run an agent on them.
if __name__ == "__main__":
	sys.stdout = os.fdopen(sys.stdout.fileno(), "w", 0)  # flush print output immediately
	agentHost = MalmoPython.AgentHost()
	agentHost.addOptionalStringArgument("recordingDir,r", "Path to location for saving mission recordings", "")

	try:
		agentHost.parse(sys.argv )
	except RuntimeError as e:
		print "ERROR:", e
		print agentHost.getUsage()
		exit(1)

	if agentHost.receivedArgument("help"):
		print agentHost.getUsage()
		exit(0)


	# Set up a recording
	numIterations = 3
	recording = False
	myMission = MalmoPython.MissionSpec(getMissionXML(), True)
	myMissionRecord = MalmoPython.MissionRecordSpec()
	recordingsDirectory = agentHost.getStringArgument("recordingDir")

	if len(recordingsDirectory) > 0:
		recording = True

		try:
			os.makedirs(recordingsDirectory)
		except OSError as exception:
			if exception.errno != errno.EEXIST: # ignore error if already existed
				raise

		myMissionRecord.recordRewards()
		myMissionRecord.recordObservations()
		myMissionRecord.recordCommands()

	# Create agent to run all the missions:
	if recording:
		myMissionRecord.setDestination(recordingsDirectory + "//" + "Mission_" + str(i) + ".tgz")

	# Start the mission:
	maxRetries = 3

	for retry in range(maxRetries):
		try:
			agentHost.startMission(myMission, myMissionRecord)
			break
		except RuntimeError as e:
			if retry == maxRetries - 1:
				print "Error starting mission:", e
				exit(1)
			else:
				time.sleep(2)

	print "Waiting for the mission to start "
	worldState = agentHost.getWorldState()

	while not worldState.has_mission_begun:
		sys.stdout.write(".")
		time.sleep(0.1)
		worldState = agentHost.getWorldState()

	print "\nMission running"



	# Setup vision handler
	obsHandler = VisionHandler(CUBE_SIZE)

	# Mission loop:
	while worldState.is_mission_running:
		if worldState.number_of_observations_since_last_state > 0:
			msg = worldState.observations[-1].text
			observations = json.loads(msg)
			pitch = observations["Pitch"]
			yaw = observations["Yaw"]

			startTime = time.time()
			obsHandler.updateFromObservation(observations[CUBE_OBS])

			# TODO: Figure out how to know if the player is crouching or not...
			playerIsCrouching = False

			# We need the eye position for filtering and to determine lookAt vector
			x, y, z = observations["XPos"], observations["YPos"], observations["ZPos"]
			y += PLAYER_EYES_CROUCHING if playerIsCrouching else PLAYER_EYES
			playerEyes = np.array([x, y, z])

			# Get the vector pointing from the eyes to the thing/block we're looking at
			lineOfSight = observations["LineOfSight"]
			block = np.array([lineOfSight["x"], lineOfSight["y"], lineOfSight["z"]])
			temp = block - playerEyes
			lookAt = getNormalizedVector(temp)

			obsHandler.filterOccluded(lookAt, playerIsCrouching)
			duration = time.time() - startTime
			# print "Handling vision took {} ms!".format(duration)

			# Print all the blocks that we can see
			print "blocks around us: \n{}".format(obsHandler.matrix)
			agentHost.sendCommand("move 1")

		for error in worldState.errors:
			print "Error:", error.text

		worldState = agentHost.getWorldState()

	print "\nMission ended!"
