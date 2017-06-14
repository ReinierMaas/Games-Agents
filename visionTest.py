# Example using vision, tries to find a tree and walks to it using controller

import MalmoPython
import os
import sys
import time
import json
import errno
import numpy as np

from util import *
from agentController import *

ENTITIES_KEY = "entities"


def getRandomTreeDetails(spawnRange = CUBE_SIZE, fixedY = 7, maxLogs = 7):
	"""
	Returns random x, y, z, numLogs (fixed y) to use as a random tree spawn. The
	spawnRange is used as an upper and lower limit to x, z, as seen from the
	origin. Notethat this function does not use x = 0 and z = 0 for a tree spawn.
	Currently, 8 logs should be set as max since that is just within attackable
	range of a player, and then we don't have to bother with having to reach
	the unreachable blocks...
	"""

	x, z = np.random.randint(1, spawnRange), np.random.randint(1, spawnRange)

	# Determine random sign for x and z
	xSign = np.random.randint(0, 2, dtype=bool)
	zSign = np.random.randint(0, 2, dtype=bool)

	if not xSign:
		x = -x

	if not zSign:
		z = -z

	numLogs = np.random.randint(3, maxLogs)		# Within attackable range...
	return x, fixedY, z, numLogs


def getTreeString(x, y, z, numLogs):
	""" Returns a Malmo string to use in the mission XML to create a crappy tree. """
	leavesHeight = y + 4
	treeHeight = y + numLogs
	return """
		<DrawingDecorator>
			<DrawSphere x="{x}" y="{yLeaves}" z="{z}" radius="3" type="leaves" />
			<DrawLine x1="{x}" y1="{y}" z1="{z}" x2="{x}" y2="{yTreeHeight}" z2="{z}" type="log" />
		</DrawingDecorator>""".format(x=x, y=y, z=z, yLeaves=leavesHeight, yTreeHeight=treeHeight)


def getMissionXML(numTrees = 2):
	""" Generates mission XML with flat world and crappy trees. """

	# Get random tree position and height (number of log blocks)
	treeList = []
	treePositions = []
	totalLogs = 0

	for tree in range(numTrees):
		x, y, z, numLogs = getRandomTreeDetails()
		treePositions.append(np.array([x, y, z]))
		treeList.append(getTreeString(x, y, z, numLogs))
		totalLogs += numLogs

	print "Number of logs that will be spawned = {}".format(totalLogs)
	treeString = "".join(treeList)

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
					{treeString}
					<ServerQuitWhenAnyAgentFinishes />
					<ServerQuitFromTimeUp timeLimitMs="60000" description="Ran out of time." />
				</ServerHandlers>
			</ServerSection>

			<AgentSection mode="Survival">
				<Name>MalmoSucksBalls</Name>
				<AgentStart>
					<Placement x="0.5" y="7.0" z="0.5" yaw="90" />
				</AgentStart>

				<AgentHandlers>
					<AbsoluteMovementCommands/>
					<ContinuousMovementCommands />
					<InventoryCommands />
					<MissionQuitCommands />

					<ObservationFromFullStats />
					<ObservationFromNearbyEntities>
						<Range name="{entitiesName}" xrange="30" yrange="30" zrange="30"/>
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
		</Mission>""".format(treeString=treeString, entitiesName=ENTITIES_KEY,
			gridName=CUBE_OBS, gridSize=CUBE_SIZE), treePositions


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

	# Start the mission, FOREVER:
	while True:
		missionXML, treePositions = getMissionXML()
		myMission = MalmoPython.MissionSpec(missionXML, True)
		myMissionRecord = setupRecording(agentHost)
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

		print "\nMission running - Spawned random tree for agent to chop down"
		time.sleep(1.0)		# To allow observations and rendering to become ready


		# Setup agent handler and chopped trees stuff
		agent = AgentController(agentHost)
		treePos = treePositions[0]
		print "Using treePos = {}".format(treePos)
		agent.controller.setPitch(20.0)

		# Mission loop:
		while worldState.is_mission_running:
			if worldState.number_of_observations_since_last_state > 0:
				# Get observation info
				msg = worldState.observations[-1].text
				observation = json.loads(msg)
				# print "observation = {}".format(observation)

				# if ENTITIES_KEY in observation:
				# 	print "entities = {}".format(observation[ENTITIES_KEY])

				if u"XPos" not in observation:
					print "Fuck you Malmo, gimme mah playahPos"
					time.sleep(0.1)
					continue

				agent.updateObservation(observation)

				if u"LineOfSight" in observation:
					print "LOS = {}".format(observation[u"LineOfSight"])
					# TODO: Finish function below and scrap everything below it...
					agent.chopTree(observation[u"LineOfSight"], treePos)
				else:
					print "Y U NO GIVE LINEOFSIGHT?"

				# continue

				# playerPos = getPlayerPos(observation, False)
				# usablePlayerPos = getPlayerPos(observation, True)

				# # Look for wood
				# woodPositions = agent.findWood()

				# if len(woodPositions) == 0:
				# 	# Shit, no wood visible/in range... keep moving then
				# 	# print "No wood in range!"
				# 	agent.controller.setPitch(0)
				# 	agent.controller.moveForward()
				# 	agent.controller.setAttackMode(False)

				# 	# Check if we can collect some wood spoils, and pick them up...
				# 	if ENTITIES_KEY in observation:
				# 		woodDropPositions = getEntityPositions(playerPos,
				# 			observation[ENTITIES_KEY], BLOCK_WOOD)

				# 		if woodDropPositions != []:
				# 			agent.controller.lookAt(woodDropPositions[0])
				# 			agent.controller.moveForward()
				# 		else:
				# 			print "Chopped tree down and collected all wood!"
				# 			agent.controller.setPitch(0)
				# 			agent.controller.stopMoving()
				# 			time.sleep(1.5)
				# 			agentHost.sendCommand("quit")

				# else:
				# 	# Look at the first wood block
				# 	usableWoodPos = usablePlayerPos + woodPositions[0]
				# 	realWoodPos = playerPos + woodPositions[0]
				# 	tempx, tempy, tempz = woodPositions[0]
				# 	agent.controller.lookAt(realWoodPos)

				# 	# Check line of sight to see if we have targeted the right block
				# 	if u"LineOfSight" in observation:
				# 		lineOfSightDict = observation[u"LineOfSight"]
				# 		losBlock = getLineOfSightBlock(lineOfSightDict)
				# 		relBlockPos = losBlock - usablePlayerPos
				# 		x, y, z = relBlockPos
				# 		visionBlockIsWood = agent.visionHandler.isBlock(x, y, z,
				# 			BLOCK_WOOD)
				# 		losBlockType = lineOfSightDict[u"type"]

				# 		# If we are standing close enough to the wood block, start
				# 		# punching it,
				# 		inRange = lineOfSightDict[u"inRange"]

				# 		if inRange and ((losBlock == usableWoodPos).all() or \
				# 		visionBlockIsWood or losBlockType == BLOCK_WOOD):

				# 			print "Chopping tree down!!!!"
				# 			agent.controller.stopMoving()
				# 			agent.controller.lookAt(realWoodPos)
				# 			agent.controller.setAttackMode(True)
				# 		else:
				# 			# If the distance between the wood block and our position
				# 			# is too far away, we need to towards it
				# 			agent.controller.setAttackMode(False)
				# 			distanceEpsilon = 0.9
				# 			distanceToWood = distanceH(playerPos, realWoodPos)

				# 			# Malmo already clips speeds > 1.0 to 1.0 maximum
				# 			movementSpeed = distanceToWood / 3.0

				# 			if distanceToWood > distanceEpsilon:
				# 				# Keep moving forward until we reach it
				# 				print "Moving towards new wood, possibly like a fucking moron! Speed = {}".format(
				# 					movementSpeed)
				# 				agent.controller.moveForward(movementSpeed)

			for error in worldState.errors:
				print "Error:", error.text

			worldState = agentHost.getWorldState()

		print "\nMission ended!"
