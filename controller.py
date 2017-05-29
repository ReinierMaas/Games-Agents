# Main code for handling walking around and controlling the agent

# Assumes:
# <ObservationFromFullStats/>
# <ContinuousMovementCommands turnSpeedDegs="180"/>
# observations.get("Yaw", 0)

import MalmoPython
import numpy as np

from math import *


class Controller(object):
	""" Class used for controlling agent movement. """

	def __init__(self, agent):
		self.agent = agent
		self.currentHotbar = 0
		self.yaw = 0.0
		self.pitch = 0.0
		self.location = np.array([0, 0, 0], dtype=float)

	def getLocation(self):
		return (self.location[0], self.location[1], self.location[2])

	def update(self, observation):
		""" Updates agent pitch, yaw and position based on observation. """
		if observation is not None:
			self.yaw = observation.get(u"Yaw", 0)
			self.pitch = observation.get(u"Pitch", 0)
			x, y, z = observation.get(u"XPos", 0), observation.get(u"YPos", 0), \
				observation.get(u"ZPos", 0)
			self.location = np.array([x, y, z])


	def selectHotbar(self, hotbar):
		""" Selects a given hotbar. Note that the first hotbar is element 1! """
		self.agent.sendCommand("hotbar.{} 1".format(hotbar))
		self.agent.sendCommand("hotbar.{} 0".format(hotbar))
		currentHotbar = hotbar


	def pitchByAngle(self, angle):
		""" Pitch by a given angle (approx). """
		self.setPitch(self.pitch + angle)


	def turnByAngle(self, angle):
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

	def lookAtVertically(self, position):
		dx, dy, dz = self.location[0] - position[0], \
			self.location[1] - position[1], self.location[2] - position[2]
		dh = sqrt(dx**2 + dz**2)
		ptch = degrees(atan2(dy, dh))
		self.setPitch(ptch)

	def lookAt(self, position)
		self.lookAtVertically(position)
		self.lookAtHorizontally(position)
