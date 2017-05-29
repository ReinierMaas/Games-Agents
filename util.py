# Utility file with utility code and functions

from math import sqrt, fsum


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
