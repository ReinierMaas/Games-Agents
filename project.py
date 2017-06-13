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
from navigation import *
from stateMachine import *
import worldGen

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

INTERESTING_BLOCKS = ["log"]
def getInterestingBlocks(visionHandler):
	blocks = []
	for tag in INTERESTING_BLOCKS:
		blocks.extend([(x,tag) for x in visionHandler.findBlocks(tag)])

	return blocks

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


# --- Main --- #

if __name__ == "__main__":
	sys.stdout = os.fdopen(sys.stdout.fileno(), "w", 0)  # flush print output immediately

	# Setup agent host
	agentHost = getAgentHost()
	lake = [worldGen.makeLake(0, 7, 25, 15, 8)]
	trees = [worldGen.makeTree(-5, 7, 0), worldGen.makeTree(5, 7, 0)]
	decs = lake + trees
	decorator = worldGen.makeDecorator(decs)
	missionXML = worldGen.getMissionXML(worldGen.getFlatWorldGenerator(), \
		decorator)
	myMission = MalmoPython.MissionSpec(missionXML, True)

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


	print "CUBE_SIZE{}".format(CUBE_SIZE)
	# Setup vision handler, controller, etc
	visionHandler = VisionHandler(CUBE_SIZE)
	controller = Controller(agentHost)
	navGraph = Graph(150, 150, 1)
	navigator = Navigator(controller)
	navigator.setNavGraph(navGraph)

	startTime = time.time()
	routeSet = False
	# Mission loop:
	while worldState.is_mission_running:
		if worldState.number_of_observations_since_last_state > 0:
			msg = worldState.observations[-1].text
			observation = json.loads(msg)
			pitch = observation[u"Pitch"]
			yaw = observation[u"Yaw"]

			# TODO: Figure out how to know if the player is crouching or not...
			playerIsCrouching = False
			lookAt = getLookAt(observation, playerIsCrouching)

			# Update vision and filter occluded blocks
			controller.update(observation)

			visionHandler.updateFromObservation(observation[CUBE_OBS])
			visionHandler.filterOccluded(lookAt, playerIsCrouching)
			playerPos = controller.location

			walkable = visionHandler.getWalkableBlocks()
			#print len(walkable)
			interestingBlocks = getInterestingBlocks(visionHandler)

			navigator.updateFromVision(walkable, interestingBlocks, CUBE_SIZE)
			if not navigator.update(autoMove = True):
				routeSet = False


			if time.time() - startTime > 20 and not routeSet:
				startWp = navigator.lastWaypoint
				routeSet = True
				route = findRouteByKey(startWp, "log")
				if route is not None:
					print route
					navigator.setRoute(route)


			# # Print all the blocks that we can see
			# print "blocks around us: \n{}".format(visionHandler.matrix)

			# # Look for wood
			# woodPositions = visionHandler.findWood()
			# print "playerPos = {}, woodPositions = \n{}".format(playerPos, woodPositions)

			# if woodPositions == []:
			# 	# Shit, no wood visible/in range... keep moving then
			# 	print "No wood in range!"
			# 	agentHost.sendCommand("move 1")
			# else:
			# 	# Walk to the first wood block
			# 	realWoodPos = getRealPosFromRelPos(playerPos, woodPositions[0])
			# 	print "Wood found at relative position {} and absolute position {}".format(
			# 		woodPositions[0], realWoodPos)
			# 	controller.lookAtHorizontally(realWoodPos)
			# 	agentHost.sendCommand("move 1")

		for error in worldState.errors:
			print "Error:", error.text

		worldState = agentHost.getWorldState()

	print "\nMission ended!"
