# Example using vision, tries to find a tree and walks to it using controller

import MalmoPython
import os
import sys
import time
import json
import errno
import numpy as np

from util import *
from controller import *
from vision import *

ENTITIES_KEY = "entities"


def getRandomTreeSpawnPos(spawnRange = CUBE_SIZE, fixedY = 7):
	"""
	Returns random x, z (fixed y) to use as a random tree spawn. The spawnRange
	is used as an upper and lower limit to x, z, as seen from the origin. Note
	that this function does not use x = 0 and z = 0 for a tree spawn.
	"""

	x, z = np.random.randint(1, spawnRange), np.random.randint(1, spawnRange)

	# Determine random sign for x and z
	xSign = np.random.randint(0, 2, dtype=bool)
	zSign = np.random.randint(0, 2, dtype=bool)

	if not xSign:
		x = -x

	if not zSign:
		z = -z

	return x, fixedY, z


def getMissionXML():
	""" Generates mission XML with flat world and 1 crappy tree. """

	# Get random tree position and height (number of log blocks)
	x, y, z = getRandomTreeSpawnPos()
	numLogs = np.random.randint(1, CUBE_SIZE)	# Within vision range...


	return """<?xml version="1.0" encoding="UTF-8" ?>
		<Mission xmlns="http://ProjectMalmo.microsoft.com" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
			<About>
				<Summary>Test filtering of visible blocks and finding visible trees</Summary>
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
						<DrawSphere x="{x}" y="{yLeaves}" z="{z}" radius="3" type="leaves" />
						<DrawLine x1="{x}" y1="{y}" z1="{z}" x2="{x}" y2="{yTreeHeight}" z2="{z}" type="log" />

						<DrawLine x1="-6" y1="7" z1="-1" x2="-6" y2="7" z2="1" type="stone" />
						<DrawLine x1="-6" y1="8" z1="-1" x2="-6" y2="8" z2="1" type="glass" />
					</DrawingDecorator>

					<ServerQuitWhenAnyAgentFinishes />
					<ServerQuitFromTimeUp timeLimitMs="60000" description="Ran out of time." />
				</ServerHandlers>
			</ServerSection>

			<AgentSection mode="Survival">
				<Name>YourMom</Name>
				<AgentStart>
					<Placement x="0.5" y="7.0" z="0.5" yaw="90" />
				</AgentStart>

				<AgentHandlers>
					<AbsoluteMovementCommands/>
					<ContinuousMovementCommands />
					<InventoryCommands />

					<ObservationFromFullStats />
					<ObservationFromNearbyEntities>
						<Range name="{entitiesName}" xrange="40" yrange="40" zrange="40"/>
					</ObservationFromNearbyEntities>
					<ObservationFromRay />
					<ObservationFromHotBar />
					<ObservationFromGrid>
						<Grid name="{gridName}">
							<min x="-{gridSize}" y="-{gridSize}" z="-{gridSize}"/>
							<max x="{gridSize}" y="{gridSize}" z="{gridSize}"/>
						</Grid>
					</ObservationFromGrid>
				</AgentHandlers>
			</AgentSection>
		</Mission>""".format(x=x, y=y, z=z, yLeaves=y+4, yTreeHeight=y+numLogs+2,
			entitiesName=ENTITIES_KEY, gridName=CUBE_OBS, gridSize=CUBE_SIZE)


def getAgentHost():
	""" Creates agent host connection and parses commandline arguments. """
	agentHost = MalmoPython.AgentHost()
	agentHost.addOptionalStringArgument("recordingDir,r", "Path to location " + \
		"for saving mission recordings", "")

	try:
		agentHost.parse(sys.argv )
	except RuntimeError as e:
		print "ERROR:", e
		print agentHost.getUsage()
		exit(1)

	if agentHost.receivedArgument("help"):
		print agentHost.getUsage()
		exit(0)

	return agentHost


def setupRecording(agentHost):
	""" If commandline arguments specify it, setup recording of this agent. """
	recording = False
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

	if recording:
		myMissionRecord.setDestination(recordingsDirectory + "//" + "Mission_" + str(i) + ".tgz")

	return myMissionRecord


# Create a simple flatworld mission and run an agent on them.
if __name__ == "__main__":
	sys.stdout = os.fdopen(sys.stdout.fileno(), "w", 0)  # flush print output immediately

	# Setup agent host
	agentHost = getAgentHost()
	myMission = MalmoPython.MissionSpec(getMissionXML(), True)

	# Optionally, set up a recording
	myMissionRecord = setupRecording(agentHost)

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
	time.sleep(0.5)		# To allow observations and rendering to become ready


	# Setup vision handler, controller, etc
	visionHandler = VisionHandler(CUBE_SIZE)
	controller = Controller(agentHost)

	# Mission loop:
	while worldState.is_mission_running:
		if worldState.number_of_observations_since_last_state > 0:
			# Get observation info
			msg = worldState.observations[-1].text
			observation = json.loads(msg)
			# print "observation = {}".format(observation)

			if ENTITIES_KEY in observation:
				print "entities = {}".format(observation[ENTITIES_KEY])

			playerIsCrouching = controller.isCrouching()
			lookAt = getLookAt(observation, playerIsCrouching)

			# Update vision and filter occluded blocks
			controller.update(observation)
			controller.setCrouch(False)
			visionHandler.updateFromObservation(observation[CUBE_OBS])
			visionHandler.filterOccluded(lookAt, playerIsCrouching)
			playerPos = getPlayerPos(observation, False)
			usablePlayerPos = getPlayerPos(observation, True)
			# print "playerPos = {}, round = {}, final = {}".format(playerPos,
			# 	np.round(playerPos, 0), usablePlayerPos)

			# Print all the blocks that we can see
			# print "blocks around us: \n{}".format(visionHandler)

			# Look for wood
			woodPositions = visionHandler.findWood()

			if woodPositions == []:
				# Shit, no wood visible/in range... keep moving then
				# print "No wood in range!"
				controller.setPitch(0)
				agentHost.sendCommand("move 1")
				agentHost.sendCommand("attack 0")

				# Check to see if we can collect some wood spoils...

			else:
				# Look at the first wood block
				usableWoodPos = usablePlayerPos + woodPositions[0]
				realWoodPos = playerPos + woodPositions[0]
				# print "usableWoodPos = {}, realWoodPos = {}".format(usableWoodPos,
				# 	realWoodPos)
				tempx, tempy, tempz = woodPositions[0]
				# print "wood[0] at {}, {}, {}: {}".format(tempx, tempy, tempz,
				# 	visionHandler.isBlock(tempx, tempy, tempz, BLOCK_WOOD))

				# print "Target wood found at relative position {} and absolute position {}".format(
				# 	woodPositions[0], usableWoodPos)

				controller.lookAt(realWoodPos)

				# Check line of sight to see if we have targeted the right block
				if u"LineOfSight" in observation:
					lineOfSightDict = observation[u"LineOfSight"]
					losBlock = getLineOfSightBlock(lineOfSightDict)
					relBlockPos = losBlock - usablePlayerPos
					x, y, z = relBlockPos
					visionBlockIsWood = visionHandler.isBlock(x, y, z, BLOCK_WOOD)
					losBlockType = lineOfSightDict[u"type"]
					print "LOS block = {}, LOS type = {}, isWood = {}, target = {}".format(
						losBlock, losBlockType, visionBlockIsWood, usableWoodPos)

					# If we are standing close enough to the wood block, start
					# punching it,
					inRange = lineOfSightDict[u"inRange"]
					# print "relBlockPos = {} {} {}, inRange = {}".format(x, y, z,
					# 	inRange)

					if inRange and ((losBlock == usableWoodPos).all() or visionBlockIsWood or losBlockType == BLOCK_WOOD):
						# print "Chopping tree down!!!!"
						agentHost.sendCommand("move 0")
						agentHost.sendCommand("attack 1")
					else:
						# If the distance between the wood block and our position
						# is too far away, we need to towards it
						print "MURT! distanceH is {}".format(distanceH(playerPos, realWoodPos))
						agentHost.sendCommand("attack 0")

						if distanceH(playerPos, realWoodPos) > sqrt(2) - 0.1:
							# Keep moving forward until we reach it
							# print "Moving towards new wood!"
							controller.lookAt(realWoodPos)
							agentHost.sendCommand("move 1")


		for error in worldState.errors:
			print "Error:", error.text

		worldState = agentHost.getWorldState()

	print "\nMission ended!"
