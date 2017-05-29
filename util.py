# Utility file with utility code and functions

import numpy as np

from math import sqrt, fsum

# Some constants that can be useful
PLAYER_EYES = 1.625  			# Player's eyes are at y = 1.625 blocks high
PLAYER_EYES_CROUCHING = 1.5		# Player's eyes are at y = 1.5 when crouching


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


def getPlayerPos(observation):
	""" Returns the position of the player from the observation as a np array. """
	x, y, z = observation["XPos"], observation["YPos"], observation["ZPos"]
	return np.array([x, y, z])


def getLookAt(observation, playerIsCrouching):
	""" Returns the non-normalized lookAt vector as seen from the player's eyes. """

	# Get position of the player's eyes
	playerPos = getPlayerPos(observation)
	y = PLAYER_EYES_CROUCHING if playerIsCrouching else PLAYER_EYES
	playerEyesPos = playerPos + np.array([0, y, 0])

	# Get the vector pointing from the eyes to the thing/block we're looking at
	lineOfSight = observation["LineOfSight"]
	block = np.array([lineOfSight["x"], lineOfSight["y"], lineOfSight["z"]])
	lookAt = block - playerEyesPos
	return lookAt
