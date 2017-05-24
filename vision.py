# Code for filtering non-visible blocks based on a given observation and small tests

import MalmoPython
import os
import random
import sys
import time
import json
import copy
import errno
import math
import xml.etree.ElementTree
import numpy as np

# Configuration for observation cube, with name in XML/JSON and size in 1 direction
CUBE_OBS = "cube10"
CUBE_SIZE = 1

PLAYER_EYES = 1.625  	# Player"s eyes are at y = 1.625 blocks from the ground
FOV = 70				# Default Field of View for Minecraft


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
		self.matrix = np.zeros((self.realSize, self.realSize, self.realSize),
			dtype="|S25")	# 25 characters should be enough for block names...
		self.center = size


	def getBlockAtRelPos(self, relX, relY, relZ):
		"""
		Returns the block at the given x, y, z position relative to the player.
		Does not check if the position lies inside the cube! The following should
		hold: -size <= x, y, z <= size
		"""
		return self.matrix[self.center + relX, self.center + relY, self.center + relZ]


	def updateFromObservation(self, cubeObservation):
		"""
		Converts the 1D list of blocks into our 3D matrix. Don't forget to call
		filterOccluded() afterwards!
		"""

		# Sanity check, just in case
		if len(cubeObservation) != self.numElements:
			raise ValueError("cube observation uses different cube size!")

		# Fill the matrix with observation values manually
		x = y = z = -self.size

		for i in range(self.numElements):
			self.matrix[self.center + x, self.center + y, self.center + z] = cubeObservation[i]
			i += 1

			# Update x, y, z coordinates
			x += 1

			if x > self.size:
				# Wrap-around x, update z
				x = -self.size
				z += 1

				if z > self.size:
					# Wrap-around z, update y
					z = -self.size
					y += 1

		# Another method is to directly copy over the list to a numpy matrix,
		# reset the shape, and index using x, z, y, but this is less error-prone :P
		# self.matrix = np.reshape(np.array(cubeObservation), (self.size, self.size, self.size))
		# self.matrix[self.center + x, self.center + z, self.center + y]


	def filterOccluded(self, pitch, yaw):
		""" Filters out all occluded blocks that the agent cannot see. """

		# TODO: Finish this... Keep pitch, yaw en horizontal en vertical FOV in mind...
		# Pitch = vertical angle
		# Yaw = horizontal angle




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
						<StartTime>12000</StartTime>
						<AllowPassageOfTime>false</AllowPassageOfTime>
					</Time>

					<Weather>clear</Weather>
				</ServerInitialConditions>

				<ServerHandlers>
					<FlatWorldGenerator generatorString="3;7,5*3,2;1;" forceReset="true" />

					<DrawingDecorator>
						<DrawSphere x="-5" y="11" z="0" radius="3" type="leaves" />
						<DrawLine x1="-5" y1="7" z1="0" x2="-5" y2="11" z2="0" type="log" />
					</DrawingDecorator>

					<ServerQuitWhenAnyAgentFinishes />
					<ServerQuitFromTimeUp timeLimitMs="50000" description="Ran out of time." />
				</ServerHandlers>
			</ServerSection>

			<AgentSection mode="Survival">
				<Name>Your Mom</Name>
				<AgentStart>
					<Placement x="0.5" y="7.0" z="0.5" yaw="90" />
				</AgentStart>

				<AgentHandlers>
					<DiscreteMovementCommands />
					<InventoryCommands />
					<ObservationFromFullStats />
					<ObservationFromRay />
					<ObservationFromHotBar />
					<ObservationFromGrid>
						<Grid name="floor3x3">
							<min x="-1" y="-1" z="-1"/>
							<max x="1" y="-1" z="1"/>
						</Grid>

						<Grid name="{0}">
							<min x="-{1}" y="-{1}" z="-{1}"/>
							<max x="{1}" y="{1}" z="{1}"/>
						</Grid>
					</ObservationFromGrid>
				</AgentHandlers>
			</AgentSection>
		</Mission>""".format(CUBE_OBS, CUBE_SIZE)


# Create a simple flatworld mission and run an agent on them.
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

# Mission loop:
obsHandler = VisionHandler(CUBE_SIZE)

while worldState.is_mission_running:
	if worldState.number_of_observations_since_last_state > 0:
		msg = worldState.observations[-1].text
		observations = json.loads(msg)

		# print("msg = {}".format(msg))
		obsHandler.updateFromObservation(observations[CUBE_OBS])
		# print "cube = {}".format(observations[CUBE_OBS])
		# print "matrix = {}".format(obsHandler.matrix)

		print "dirt block: {}".format(obsHandler.getBlockAtRelPos(-1, -1, 0))
		agentHost.sendCommand("move 1")

	for error in worldState.errors:
		print "Error:", error.text

	worldState = agentHost.getWorldState()

print "\nMission ended!"
