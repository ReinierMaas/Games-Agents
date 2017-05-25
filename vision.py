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
CUBE_SIZE = 2

PLAYER_EYES = 1.625  	# Player"s eyes are at y = 1.625 blocks from the ground
FOV = 70				# Default Field of View for Minecraft


TRANSPARANT_BLOCKS = ["glass", "air", "sapling", "cobweb", "flower", "mushroom",
	"torch", "ladder", "fence", "iron_bars", "glass_pane", "vines", "lily_pad",
	"sign", "item_frame", "flower_pot", "skull", "armor_stand", "banner",
	"lever", "pressure_plate", "redstone_torch", "button", "trapdoor", "tripwire",
	"tripwire_hook", "redstone", "rail", "beacon", "cauldron", "brewing_stand"]

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
		Returns empty string if -size > x, y, z or x, y, z > size (out of bounds).
		This also corresponds to "we don't know whats there".
		"""
		if relX < -self.size or relX > self.size:
			return ""

		if relY < -self.size or relY > self.size:
			return ""

		if relZ < -self.size or relZ > self.size:
			return ""

		return self.matrix[self.center + relX, self.center + relY, self.center + relZ]


	def updateFromObservation(self, cubeObservation):
		"""
		Converts the 1D list of blocks into our 3D matrix. Don't forget to call
		filterOccluded() afterwards!
		"""

		cube = [
		u'grass', u'grass', u'grass',		# x = -1 to 1, y = -1, z = -1
		u'dirt',  u'grass', u'grass',		# x = -1 to 1, y = -1, z = 0
		u'grass', u'grass', u'grass',		# x = -1 to 1, y = -1, z = 1

		u'air', u'air', u'air',				# x = -1 to 1, y = 0, z = -1
		u'log', u'air', u'air',				# x = -1 to 1, y = 0, z = 0	 (middle = center)
		u'air', u'air', u'air',				# x = -1 to 1, y = 0, z = 1

		u'air', u'air', u'air',				# x = -1 to 1, y = 1, z = -1
		u'log', u'air', u'air',				# x = -1 to 1, y = 1, z = 0
		u'air', u'air', u'air']				# x = -1 to 1, y = 1, z = 1

		# Sanity check, just in case
		if len(cubeObservation) != self.numElements:
			raise ValueError("cube observation uses different cube size!")

		# Directly copy over the list to a numpy matrix, reset the shape, and
		# swap the y and z axes (previous index / Malmo uses x, z, y)
		temp = np.array(cubeObservation)
		temp = np.reshape(temp, (self.realSize, self.realSize, self.realSize))
		self.matrix = np.swapaxes(temp, 1, 2)


	def filterOccluded(self, pitch, yaw):
		""" Filters out all occluded blocks that the agent cannot see. """

		# First we filter out all blocks that are not adjacent to a transparant
		# block, since they will not be visible anyway. We do this by starting
		# from the players eyes, and gradually marking visible/unvisible blocks
		# outwards.
		visible = np.zeros((self.realSize, self.realSize, self.realSize), dtype=bool)


		def isVisible(relX, relY, relZ):
			""" Returns true/false if the given relative x, y, z block is visible. """
			return visible[self.center + relX, self.center + relY, self.center + relZ]

		def setVisible(relX, relY, relZ):
			""" Sets the given relative x, y, z block to visible """
			visible[self.center + relX, self.center + relY, self.center + relZ] = True

		def setInvisible(relX, relY, relZ):
			""" Sets the block at relative x, y, z coordinates to empty string. """
			visible[self.center + relX, self.center + relY, self.center + relZ] = False
			self.matrix[self.center + relX, self.center + relY, self.center + relZ] = ""


		# The blocks where the player is standing is always visible of course...
		# Unless we are suffocating... in which case we're fucked...
		# Future TODO: Figure something out or not, I dont care
		visible[self.center, self.center, self.center] = True
		visible[self.center, self.center + 1, self.center] = True

		# We basically expand our search for visible blocks outward from where
		# the player is standing, and check adjacant blocks to see if they are
		# visible.
		# There are edge cases in which a block is not marked visible because
		# none of its neighbors have been marked as such, but they are in fact
		# potentially visible since its neighbors will be marked visible later
		# on. We can either fix this by doing multiple passes (easy), or by
		# changing the loops to work in an actual, outwards spiral (harder)...
		# TODO: Fix edge cases
		for x in range(0, self.size + 1) + range(0, -self.size - 1, -1):
			for y in range(0, self.size + 1) + range(0, -self.size - 1, -1):
				for z in range(0, self.size + 1) + range(0, -self.size - 1, -1):

					# If this block is already visible, skip it
					if isVisible(x, y, z):
						continue

					# Check 6 surrounding blocks if they're visible. Blocks that
					# are out of bounds will be empty strings, which is fine.
					if x + 1 < self.size and isVisible(x + 1, y, z) and \
					self.getBlockAtRelPos(x + 1, y, z) in TRANSPARANT_BLOCKS:

						setVisible(x, y, z)
						continue

					if x - 1 > -self.size and isVisible(x - 1, y, z) and \
					self.getBlockAtRelPos(x - 1, y, z) in TRANSPARANT_BLOCKS:

						setVisible(x, y, z)
						continue


					if y + 1 < self.size and isVisible(x, y + 1, z) and \
					self.getBlockAtRelPos(x, y + 1, z) in TRANSPARANT_BLOCKS:

						setVisible(x, y, z)
						continue

					if y - 1 > -self.size and isVisible(x, y - 1, z) and \
					self.getBlockAtRelPos(x, y - 1, z) in TRANSPARANT_BLOCKS:

						setVisible(x, y, z)
						continue


					if z + 1 < self.size and isVisible(x, y, z + 1) and \
					self.getBlockAtRelPos(x, y, z + 1) in TRANSPARANT_BLOCKS:

						setVisible(x, y, z)
						continue

					if z - 1 > -self.size and isVisible(x, y, z - 1) and \
					self.getBlockAtRelPos(x, y, z - 1) in TRANSPARANT_BLOCKS:

						setVisible(x, y, z)
						continue

					# This block is likely not visible!
					# print "block x = {}, y = {}, z = {} is not visible!".format(x, y, z)
					setInvisible(x, y, z)

		# Now we filter out all the blocks are not visible because of our view
		# TODO: Finish this... Keep pitch, yaw, and horizontal and vertical FOV in mind...
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

	# Mission loop:
	obsHandler = VisionHandler(CUBE_SIZE)

	# For later on
	steppedLeft = False

	while worldState.is_mission_running:
		if worldState.number_of_observations_since_last_state > 0:
			msg = worldState.observations[-1].text
			observations = json.loads(msg)

			# print("msg = {}".format(msg))

			obsHandler.updateFromObservation(observations[CUBE_OBS])
			# print "cube = {}".format(observations[CUBE_OBS])
			print "matrix1 = {}".format(obsHandler.matrix)
			obsHandler.filterOccluded(None, None)
			print "matrix2 = {}".format(obsHandler.matrix)

			# print "dirt block: {}".format(obsHandler.getBlockAtRelPos(-1, -1, 0))

			# Check if we have reached the position in front of the tree
			x, y, z = observations["XPos"], observations["YPos"], observations["ZPos"]

			# Ugh, floating point comparisons...
			if x == -3.5 and int(y) == 7 and z == 0.5:
				print "Reached pos! x = {}, y = {}, z = {}".format(x, y, z)
				# Make 1 step to the left for science if we havent done already
				if not steppedLeft:
					agentHost.sendCommand("strafe -1")
					steppedLeft = True
					time.sleep(1.5)

			if not steppedLeft:
				agentHost.sendCommand("move 1")

		for error in worldState.errors:
			print "Error:", error.text

		worldState = agentHost.getWorldState()

	print "\nMission ended!"
