# Main code for handling walking around and controlling the agent

# Assumes:
# <ObservationFromFullStats/>
# <ContinuousMovementCommands turnSpeedDegs="180"/>
# observations.get("Yaw", 0)

import MalmoPython
import numpy as np

from util import *
from math import *


class Controller(object):
	""" Class used for controlling agent movement. """

	def __init__(self, agent):
		self.agent = agent
		self.currentHotbar = 0
		self.yaw = 0.0
		self.pitch = 0.0
		self.location = np.array([0, 0, 0], dtype=float)
		self.crouching = 0
		self.movementSpeed = 0


	def getLocation(self):
		"""Get the location as tuple"""
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

		#print "Set new yaw: {}".format(newYaw)
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
		yaw = degrees(atan2(dz, dx)) + 90.0
		self.setYaw(yaw)


	def lookAtVertically(self, position):
		eyes = np.array([0, PLAYER_EYES_CROUCHING if self.crouching else PLAYER_EYES, 0])
		dx, dy, dz = position - (self.location + eyes)
		dh = sqrt(dx**2 + dz**2)
		pitch = -degrees(atan2(dy, dh))
		self.setPitch(pitch)


	def lookAt(self, position):
		self.lookAtVertically(position)
		self.lookAtHorizontally(position)


	def setCrouchMode(self, crouching):
		""" Makes the agent crouch when True, or stops crouching when False. """
		self.crouching = int(bool(crouching))
		self.agent.sendCommand("crouch {}".format(self.crouching))


	def isCrouching(self):
		return self.crouching


	def setAttackMode(self, attacking):
		""" Makes the agent attack when True, or stops attacking when False. """
		self.attacking = int(bool(attacking))
		self.agent.sendCommand("attack {}".format(self.attacking))


	def isAttacking(self):
		return self.attacking


	def useItem(self):
		""" Makes the agent use an item/place a block """
		self.agent.sendCommand("use 1")
		self.agent.sendCommand("use 0")


	def placeBlock(self):
		""" Makes the agent place a block """
		self.useItem()


	def jump(self):
		""" Makes the agent jump once """
		self.agent.sendCommand("jump 1")
		self.agent.sendCommand("jump 0")


	def moveForward(self, movementSpeed = 1.0):
		""" Starts moving the agent forward. Ensure that movementSpeed >= 0.0 """
		self.movementSpeed = movementSpeed
		self.agent.sendCommand("move {}".format(movementSpeed))


	def stopMoving(self):
		""" Stops the agent from moving forward. """
		self.moveForward(0.0)


	def isMoving(self):
		return self.movementSpeed != 0.0

