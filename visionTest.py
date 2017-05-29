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


def getMissionXML():
	""" Generates mission XML with flat world and 1 crappy tree. """
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
						<DrawSphere x="-5" y="11" z="0" radius="3" type="leaves" />
						<DrawLine x1="-5" y1="7" z1="0" x2="-5" y2="11" z2="0" type="log" />
						<DrawLine x1="-6" y1="7" z1="-1" x2="-6" y2="7" z2="1" type="stone" />
						<DrawLine x1="-6" y1="8" z1="-1" x2="-6" y2="8" z2="1" type="glass" />
					</DrawingDecorator>

					<ServerQuitWhenAnyAgentFinishes />
					<ServerQuitFromTimeUp timeLimitMs="60000" description="Ran out of time." />
				</ServerHandlers>
			</ServerSection>

			<AgentSection mode="Creative">
				<Name>YourMom</Name>
				<AgentStart>
					<Placement x="0.5" y="7.0" z="0.5" yaw="90" />
				</AgentStart>

				<AgentHandlers>
					<AbsoluteMovementCommands/>
					<ContinuousMovementCommands />
					<InventoryCommands />

					<ObservationFromFullStats />
					<ObservationFromRay />
					<ObservationFromHotBar />
					<ObservationFromGrid>
						<Grid name="{0}">
							<min x="-{1}" y="-{1}" z="-{1}"/>
							<max x="{1}" y="{1}" z="{1}"/>
						</Grid>
					</ObservationFromGrid>
				</AgentHandlers>
			</AgentSection>
		</Mission>""".format(CUBE_OBS, CUBE_SIZE)


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
			pitch = observation["Pitch"]
			yaw = observation["Yaw"]

			# TODO: Figure out how to know if the player is crouching or not...
			playerIsCrouching = False
			lookAt = getLookAt(observation, playerIsCrouching)

			# Update vision and filter occluded blocks
			controller.update(observation)
			visionHandler.updateFromObservation(observation[CUBE_OBS])
			visionHandler.filterOccluded(lookAt, playerIsCrouching)
			playerPos = getPlayerPos(observation)

			# Print all the blocks that we can see
			print "blocks around us: \n{}".format(visionHandler.matrix)

			# Look for wood
			woodPositions = visionHandler.findWood()
			print "playerPos = {}, woodPositions = \n{}".format(playerPos, woodPositions)

			if woodPositions == []:
				# Shit, no wood visible/in range... keep moving then
				print "No wood in range!"
				agentHost.sendCommand("move 1")
			else:
				# Walk to the first wood block
				realWoodPos = playerPos + woodPositions[0] + np.array([-1, 1, 0])
				print "Wood found at relative position {} and absolute position {}".format(
					woodPositions[0], realWoodPos)
				controller.lookAtHorizontally(realWoodPos)
				agentHost.sendCommand("move 1")


		for error in worldState.errors:
			print "Error:", error.text

		worldState = agentHost.getWorldState()

	print "\nMission ended!"
