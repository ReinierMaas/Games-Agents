# Main code for handling walking around and controlling the agent

# Assumes:
# <ObservationFromFullStats/>
# <ContinuousMovementCommands turnSpeedDegs="180"/>
# observations.get("Yaw", 0)

import MalmoPython

from math import *

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


class Controller(object):
	""" Class used for controlling agent movement. """

	def __init__(self, agent):
		self.agent = agent
		self.currentHotbar = 0
		self.yaw = 0.0
		self.pitch = 0.0
		self.location = np.array([0, 0, 0], dtype=float)


	def update(self, observation):
		""" Updates agent pitch, yaw and position based on observation. """
		if observation is not None:
			self.yaw = observation.get("Yaw", 0)
			self.pitch = observation.get("Pitch", 0)
			x, y, z = observation.get("XPos", 0), observation.get("YPos", 0), \
				observation.get("ZPos", 0)
			self.location = np.array([x, y, z])


	def selectHotbar(self, hotbar):
		""" Selects a given hotbar. Note that the first hotbar is element 1! """
		self.agent.sendCommand("hotbar.{} 1".format(hotbar))
		self.agent.sendCommand("hotbar.{} 0".format(hotbar))
		currentHotbar = hotbar


	def pitch(self, angle):
		""" Pitch by a given angle (approx). """
		self.setPitch(self.pitch + angle)


	def turn(self, angle):
		""" Pitch by a given angle (approx). """
		self.setYaw(self.yaw + angle)


	def setYaw(self, newYaw):
		""" Makes the agent look at a given yaw value. """
		if int(self.yaw) == int(newYaw):
			return

		print "Set new yaw: {}".format(newYaw)
		self.agent.sendCommand("setYaw {}".format(newYaw))


	def setPitch(self, newPitch):
		""" Makes the agent look at a given pitch value. """
		if self.pitch == newPitch:
			return

		# print "Setting new pitch: {}".format(newYaw)
		self.agent.sendCommand("setPitch {}".format(newPitch))


	def lookAtHorizontally(self, position):
		""" Turns the agent to look at the given position. """
		dx, dz = self.location[0] - position[0], self.location[2] - position[2]
		yw = degrees(atan2(dz, dx)) + 90
		self.setYaw(yw)

