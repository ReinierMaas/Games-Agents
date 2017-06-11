# Utility file with utility code and functions
from __future__ import print_function
from math import *

import sys
import numpy as np



# Some constants that can be useful
PLAYER_EYES = 1.625  			# Player's eyes are at y = 1.625 blocks high
PLAYER_EYES_CROUCHING = 1.5		# Player's eyes are at y = 1.5 when crouching


# Offset in different coordinates between Malmo and Minecraft as can be
# observed from the debug screen in Minecraft itself (F3)
MALMO_OFFSET = np.array([-1, 1, 0])



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


def getVectorDistance(vector1, vector2):
	""" Returns the Euclidean distance between 2 vectors. """

	# fsum is more accurate and uses Kahan summation along with IEEE-754 fp stuff
	return sqrt(fsum([(element1 - element2)**2 for element1, element2 in zip(vector1, vector2)]))



def getRotationPitch(pitch):
	""" Returns the 3D rotation matrix for the given pitch. """
	radianPitch = radians(pitch + 90)		# Needed for cos() and sin()
	rotationPitch = np.array([
		[1, 0, 0,],
		[0, cos(radianPitch), -sin(radianPitch)],
		[0, sin(radianPitch), cos(radianPitch)]])
	return rotationPitch


def getRotationYaw(yaw):
	""" Returns the 3D rotation matrix for the given yaw. """
	radianYaw = radians(yaw + 90)
	rotationYaw = np.array([
		[cos(radianYaw), 0, sin(radianYaw)],
		[0, 1, 0],
		[-sin(radianYaw), 0, cos(radianYaw)]])
	return rotationYaw


def getRotationMatrix(pitch, yaw):
	""" Returns the 3D rotation matrix for the given pitch and yaw. """
	rotationPitch = getRotationPitch(pitch)
	rotationYaw = getRotationYaw(yaw)
	return rotationYaw * rotationPitch



def shortAngle(angle1, angle2):
	""" Returns shortest signed angle from angle1 to angle2 in degrees. """
	x, y = radians(a1), radians(a2)
	a = atan2(sin(x - y), cos(x - y))
	return degrees(a)


def distanceH(vector1, vector2):
	""" Returns horizontal distance between 2 vectors. """
	x1, z1 = vector1[0], vector1[2]
	x2, z2 = vector2[0], vector2[2]
	dx = x1 - x2
	dz = z1 - z2
	return sqrt(dx**2 + dz**2)


def distanceV(vector1, vector2):
	""" Returns vertical distance between 2 vectors. """
	return vector1[1] - vector2[1]



def getPlayerPos(observation, getIntVersion=False):
	""" Returns the position of the player from the observation as a np array. """
	x, y, z = observation[u"XPos"], observation[u"YPos"], observation[u"ZPos"]

	if getIntVersion:
		# We need to floor x and z because minecraft sucks and the coordinate
		# system is a bitch
		x, z = floor(x), floor(z)
		temp = np.round(np.array([x, y, z]), 0).astype(int)

		# print("x = {}, y = {}, z = {}, result = {}...".format(x, y, z, temp))
		return temp
	else:
		return np.array([x, y, z])


def getLookAt(observation, playerIsCrouching):
	""" Returns the non-normalized lookAt vector as seen from the player's eyes. """

	# Get position of the player's eyes
	playerPos = getPlayerPos(observation)
	y = PLAYER_EYES_CROUCHING if playerIsCrouching else PLAYER_EYES
	playerEyesPos = playerPos + np.array([0, y, 0])

	# Get the vector pointing from the eyes to the thing/block we're looking at
	lookAt = None

	if "LineOfSight" in observation:
		lineOfSight = observation[u"LineOfSight"]
		block = np.array([lineOfSight[u"x"], lineOfSight[u"y"], lineOfSight[u"z"]])
		lookAt = getNormalizedVector(block - playerEyesPos)
	else:
		# FUCKING BULLSHIT, now we have to calculate it from pitch/yaw
		pitch = observation[u"Pitch"]
		yaw = observation[u"Yaw"]
		# Calculate the rotation of the starting direction the player looks in
		startDir = np.array([1, 1, 0])		# Corresponds to pitch = yaw = 0
		rotationMatrix = getRotationMatrix(pitch, yaw)
		lookAt = getNormalizedVector(np.dot(rotationMatrix, startDir))

	return lookAt



def getLineOfSightBlock(lineOfSightDict):
	""" Returns real position of the line of sight block as an int np array. """

	# We offset x by -1.0 because minecraft has a shitty coordinate system etc
	return np.array([lineOfSightDict[u"x"] - 1.0, lineOfSightDict[u"y"],
		lineOfSightDict[u"z"]]).astype(int)



def getEntityPositions(entitiesList, entityToFind):
	"""
	Returns a list of numpy arrays where the requested entity/entities are, or
	else an empty list of no entities can be found in the list
	"""
	positionsFound = []

	for entity in entitiesList:
		if entity[u"name"] == entityToFind:
			x, y, z = entity[u"x"], entity[u"y"], entity[u"z"]
			positionsFound.append(np.array([x, y, z]))

	return positionsFound


def eprint(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)

