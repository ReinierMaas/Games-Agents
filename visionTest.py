# Example using vision, tries to find a tree and walks to it using controller

import MalmoPython
import os
import sys
import time
import json
import errno
import numpy as np

from util import *
from vision import *


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

						<Grid name="floor3x3">
							<min x="-1" y="-1" z="-1"/>
							<max x="1" y="-1" z="1"/>
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



	# Setup vision handler
	obsHandler = VisionHandler(CUBE_SIZE)

	# Mission loop:
	while worldState.is_mission_running:
		if worldState.number_of_observations_since_last_state > 0:
			msg = worldState.observations[-1].text
			observations = json.loads(msg)
			pitch = observations["Pitch"]
			yaw = observations["Yaw"]

			startTime = time.time()
			obsHandler.updateFromObservation(observations[CUBE_OBS])

			# TODO: Figure out how to know if the player is crouching or not...
			playerIsCrouching = False

			# We need the eye position for filtering and to determine lookAt vector
			x, y, z = observations["XPos"], observations["YPos"], observations["ZPos"]
			y += PLAYER_EYES_CROUCHING if playerIsCrouching else PLAYER_EYES
			playerEyes = np.array([x, y, z])

			# Get the vector pointing from the eyes to the thing/block we're looking at
			lineOfSight = observations["LineOfSight"]
			block = np.array([lineOfSight["x"], lineOfSight["y"], lineOfSight["z"]])
			temp = block - playerEyes
			lookAt = getNormalizedVector(temp)

			obsHandler.filterOccluded(lookAt, playerIsCrouching)
			duration = time.time() - startTime
			# print "Handling vision took {} ms!".format(duration)

			# Print all the blocks that we can see
			print "blocks around us: \n{}".format(obsHandler.matrix)
			agentHost.sendCommand("move 1")

		for error in worldState.errors:
			print "Error:", error.text

		worldState = agentHost.getWorldState()

	print "\nMission ended!"
