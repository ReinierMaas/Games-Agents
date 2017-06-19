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
from communication import *
from agentController import *
from goap import *

#this setting enables pre-exploration, which means all tree and lake locations
#are known to the agents at the start.
PRE_EXPLORE = True
AGENT_COUNT = 1

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


def setupAgents(NUM_AGENTS, mission):
	agents = []
	for i in range(AGENT_COUNT):
		host = getAgentHost()
		myMissionRecord = setupRecording(host)
		agents.append(Agent(i,(0,0,0), host, mission, myMissionRecord))
	return agents
# --- Main --- #

if __name__ == "__main__":
	sys.stdout = os.fdopen(sys.stdout.fileno(), "w", 0)  # flush print output immediately

	if len(sys.argv) >= 2:
		AGENT_COUNT = int(sys.argv[1])

	#generate world
	worldGen.setSeed(55)
	lakes, lakeLocs, lavaLocs = worldGen.genLakes()
	grass = worldGen.genGrass()
	trees, treelocs = worldGen.genTrees()
	decs = grass + lakes + trees
	decorator = worldGen.makeDecorator(decs)

	#create mission XML
	missionXML = worldGen.getMissionXML(worldGen.getFlatWorldGenerator(), \
		decorator, agentCount = AGENT_COUNT)
	myMission = MalmoPython.MissionSpec(missionXML, True)


	# set up a client pool
	client_pool = MalmoPython.ClientPool()
	for x in xrange(10000, 10000 + AGENT_COUNT):
		client_pool.add(MalmoPython.ClientInfo('127.0.0.1', x))

	#setup and start missions
	agents = setupAgents(AGENT_COUNT, myMission)

	for agent in agents:
		agent.startMission(client_pool)


	# Wait for missions to start:
	print "Waiting for the mission to start "
	for agent in agents:
		worldState = agent.agentHost.getWorldState()

		while not worldState.has_mission_begun:
			sys.stdout.write(".")
			time.sleep(0.1)
			worldState = agent.agentHost.getWorldState()

	print "\nMission running"
	time.sleep(0.5)		# To allow observations and rendering to become ready


	print "CUBE_SIZE{}".format(CUBE_SIZE)
	# Setup vision handler, controller, etc
	navGraph = Graph(300, 300, 1)

	for agent in agents:
		agent.agentController.navigator.setNavGraph(navGraph)
		agent.goap = Goap(agent.agentController)

	if PRE_EXPLORE:
		worldGen.bulkFlagRegion(navGraph, lakeLocs, "water", True)
		worldGen.bulkFlagRegion(navGraph, lavaLocs, "lava", True)
		worldGen.bulkFlagLoc(navGraph, treelocs, "log", True)

	startTime = time.time()
	worldStates = [None] * AGENT_COUNT
	while True:
		quit = False
		for i, agent in enumerate(agents):
			worldStates[i] = agent.agentHost.getWorldState()
			if not worldStates[i].is_mission_running:
				quit = True


		if quit:
			break

		for i, agent in enumerate(agents):
			worldState = worldStates[i]
			if worldState.number_of_observations_since_last_state > 0:
				msg = worldState.observations[-1].text
				observation = json.loads(msg)

				agent.agentController.updateObservation(observation)
				agent.agentController.navigator.update(autoMove = True)
				agent.goap.updateState()
				agent.goap.execute()


			for error in worldState.errors:
				print "Error:", error.text

	print "\nMission ended!"
