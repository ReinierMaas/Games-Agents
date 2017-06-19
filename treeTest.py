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



def getRandomTreeDetails(spawnRange = 20, fixedY = 7, maxLogs = 6):
	"""
	Returns random x, y, z, numLogs (fixed y) to use as a random tree spawn. The
	spawnRange is used as an upper and lower limit to x, z, as seen from the
	origin. Notethat this function does not use x = 0 and z = 0 for a tree spawn.
	Currently, 6 logs should be set as max since that is just within attackable
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

	numLogs = np.random.randint(3, maxLogs + 1)		# Within attackable range...
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


def getMissionXML(numTrees=2):
	""" Generates mission XML with flat world and crappy trees. """

	# Get random tree position and height (number of log blocks)
	treeList = []
	treePositions = []
	totalLogs = 0


	for tree in range(numTrees):
		x, y, z, numLogs = getRandomTreeDetails()
		treePositions.append(np.array([x, y, z]))
		treeList.append(getTreeString(x, y, z, numLogs))
		totalLogs += numLogs + 1

	print "Number of logs that will be spawned = {}".format(totalLogs)
	treeString = "".join(treeList)

	return """<?xml version="1.0" encoding="UTF-8" ?>
		<Mission xmlns="http://ProjectMalmo.microsoft.com" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
			<About>
				<Summary>Test finding trees and getting some big, hard wood</Summary>
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
					<ServerQuitFromTimeUp timeLimitMs="120000" description="Ran out of time." />
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
					<ObservationFromFullInventory/>
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

		</Mission>""".format(treeString=treeString, entitiesName=ENTITIES_OBS,
			gridName=CUBE_OBS, gridSize=CUBE_SIZE), treePositions


def getAgentHost():
	""" Creates agent host connection and parses commandline arguments. """
	agentHost = MalmoPython.AgentHost()
	agentHost.addOptionalStringArgument("recordingDir,r", "Path to location " + \
		"for saving mission recordings", "")

	try:
		agentHost.parse(sys.argv)
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
			if exception.errno != errno.EEXIST:  # ignore error if already existed
				raise

		myMissionRecord.recordRewards()
		myMissionRecord.recordObservations()
		myMissionRecord.recordCommands()

	if recording:
		myMissionRecord.setDestination(recordingsDirectory + "//" + \
			"Mission_" + str(i) + ".tgz")

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

		print "\nMission running - Spawned random trees for agent to chop down"
		time.sleep(1.0)		# To allow observations and rendering to become ready


		# Setup agent handler and first target tree
		agent = AgentController(agentHost)
		treeNr = 0
		treePos = treePositions[treeNr]
		woodLeft = True
		dropsLeft = True
		print "Using first treePos = {}".format(treePos)

		# Mission loop:
		while worldState.is_mission_running:
			if worldState.number_of_observations_since_last_state > 0:
				# Get observation info
				msg = worldState.observations[-1].text
				observation = json.loads(msg)

				if u"XPos" not in observation:
					print "Fuck you Malmo, gimme mah playahPos"
					time.sleep(0.1)
					worldState = agentHost.getWorldState()
					continue

				agent.updateObservation(observation)
				# print "Entity counts = {}".format(agent.entitiesHandler.getEntityCounts())

				if u"LineOfSight" in observation:
					if woodLeft:
						woodLeft = agent.destroyBlock(observation[u"LineOfSight"],
							BLOCK_WOOD, treePos)
					else:
						# Check if we have destroyed all the trees...
						if treeNr >= len(treePositions) - 1:
							# Check if we can collect some wood spoils, and pick them up...
							if not dropsLeft:
								print "Chopped tree down and collected all wood!"
								agent.controller.setPitch(0)
								agent.controller.stopMoving()
								agentHost.sendCommand("quit")
								time.sleep(1.5)
							else:
								dropsLeft = agent.collectDrops(BLOCK_WOOD)
						else:
							# Its likely that theres wood left, so try again
							woodLeft = True
							treeNr += 1
							treePos = treePositions[treeNr]
							print "Trying next tree nr {} at {}".format(
								treeNr + 1, treePos)
				else:
					print "Looking down because we dont have LOS info..."
					agent.controller.setPitch(45)	# Or something smarter perhaps

			for error in worldState.errors:
				print "Error:", error.text

			# Update world state and observation
			worldState = agentHost.getWorldState()

		print "\nMission ended!"
