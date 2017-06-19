# Example agent, looks around for grass and farmland, and tries to plant seeds
# on farmland and tile dirt... Looks horrible but thats because its vision
# based and it has a slight preference for negative X direction (because of the
# order in the triple loop when searching for blocks (for x, for y, for z))...
# Aka, ignore that, you can tile and plant at target positions

import MalmoPython
import os
import sys
import time
import json
import errno
import numpy as np

from util import *
from agentController import *



HOES = [u"wooden_hoe", u"stone_hoe", u"iron_hoe", u"gold_hoe", u"diamond_hoe"]
HOE_TO_FUCK = HOES[-1]			# We use the most expensive bitch hoe available
HOE_HOTBAR_SLOT = 0

SEEDS = u"wheat_seeds"			# What malmo/minecraft uses internally
NUM_SEEDS = 15
SEEDS_HOTBAR_SLOT = 1
GRASS = u"grass"
FARM_LAND = u"farmland"



def getMissionXML(numTrees=2):
	""" Generates mission XML with flat world """

	return """<?xml version="1.0" encoding="UTF-8" ?>
		<Mission xmlns="http://ProjectMalmo.microsoft.com" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
			<About>
				<Summary>Test farming seeds stuff</Summary>
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
					<ServerQuitWhenAnyAgentFinishes />
					<ServerQuitFromTimeUp timeLimitMs="120000" description="Ran out of time." />
				</ServerHandlers>
			</ServerSection>

			<AgentSection mode="Survival">
				<Name>MalmoSucksBalls</Name>
				<AgentStart>
					<Placement x="0.5" y="7.0" z="0.5" yaw="90" />

					<Inventory>
						<InventoryBlock slot="{hoeSlot}" type="{hoe}" quantity="1"/>
						<InventoryBlock slot="{seedsSlot}" type="{seeds}" quantity="{numSeeds}"/>
					</Inventory>
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

		</Mission>""".format(hoe=HOE_TO_FUCK, hoeSlot=HOE_HOTBAR_SLOT,
			seeds=SEEDS, seedsSlot=SEEDS_HOTBAR_SLOT, numSeeds = NUM_SEEDS,
			entitiesName=ENTITIES_OBS, gridName=CUBE_OBS, gridSize=CUBE_SIZE)


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
		missionXML = getMissionXML()
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

		print "\nMission running - Agent tries to tile dirt and plant seeds"
		time.sleep(1.0)		# To allow observations and rendering to become ready


		# Setup agent handler and first target grass
		agent = AgentController(agentHost)
		tiledDirt = False
		placedSeeds = False

		# Mission loop:
		while worldState.is_mission_running:
			if worldState.number_of_observations_since_last_state > 0:
				# Get observation info
				msg = worldState.observations[-1].text
				observation = json.loads(msg)
				# print "observation = {}".format(observation)

				if u"XPos" not in observation:
					print "Fuck you Malmo, gimme mah playahPos"
					time.sleep(0.1)
					worldState = agentHost.getWorldState()
					continue

				agent.updateObservation(observation)

				# Check if we have enough seeds left
				if not agent.inventoryHandler.hasItemInHotbar(SEEDS):
					print "\n\nWe've run out of seeds... Time to give up on life... Goodbye fuckers\n\n"
					agentHost.sendCommand("quit")
					time.sleep(1.5)

				# Get positions of grass and farmland for agent so we can farm
				relGrassPositions = agent.visionHandler.findBlocks(GRASS)
				relFarmLandPositions = agent.visionHandler.findBlocks(FARM_LAND)

				if len(relFarmLandPositions) > 0:
					agent.controller.selectHotbar(SEEDS_HOTBAR_SLOT)
					farmLandPos = agent.playerPos + relFarmLandPositions[0]
					placedSeeds = agent.useItem(farmLandPos)

					if placedSeeds:
						# print "Planted seeds at {}".format(farmLandPos)
						pass
					else:
						# print "Trying to plant seeds at {}".format(farmLandPos)
						pass
				elif len(relGrassPositions) > 0:
					agent.controller.selectHotbar(HOE_HOTBAR_SLOT)
					grassPos = agent.playerPos + relGrassPositions[0]
					tiledDirt = agent.placeBlock(grassPos)

					if tiledDirt:
						# print "Tiled dirt at {}".format(grassPos)
						pass
					else:
						# print "Trying to tile dirt at {}".format(grassPos)
						pass
				else:
					print "No farmland and grass in sight!"

			for error in worldState.errors:
				print "Error:", error.text

			# Update world state and observation
			worldState = agentHost.getWorldState()

		print "\nMission ended!"
