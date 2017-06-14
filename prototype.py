# ------------------------------------------------------------------------------------------------
# Copyright (c) 2016 Microsoft Corporation
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
# associated documentation files (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge, publish, distribute,
# sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or
# substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT
# NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
# ------------------------------------------------------------------------------------------------

# Tutorial sample #2: Run simple mission using raw XML

import MalmoPython
import os
import sys
import time
from controller import *
from navigation import *
from stateMachine import *
import random

sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)  # flush print output immediately

# More interesting generator string: "3;7,44*49,73,35:1,159:4,95:13,35:13,159:11,95:10,159:14,159:6,35:6,95:6;12;"

missionXML = '''<?xml version="1.0" encoding="UTF-8" standalone="no" ?>
			<Mission xmlns="http://ProjectMalmo.microsoft.com" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">

			  <About>
				<Summary>Hello world!</Summary>
			  </About>

			  <ServerSection>
				<ServerHandlers>
				  <FlatWorldGenerator generatorString="3;7,220*1,5*3,2;3;,biome_1"/>
				  <ServerQuitFromTimeUp timeLimitMs="3000000"/>
				  <ServerQuitWhenAnyAgentFinishes/>
				</ServerHandlers>
			  </ServerSection>

			  <AgentSection mode="Survival">
				<Name>MalmoTutorialBot</Name>
				<AgentStart/>
				<AgentHandlers>
				  <ObservationFromFullStats/>
				  <AbsoluteMovementCommands/>
				  <ContinuousMovementCommands />
				</AgentHandlers>
			  </AgentSection>
			</Mission>'''

# Create default Malmo objects:

agent_host = MalmoPython.AgentHost()
try:
    agent_host.parse(sys.argv)
except RuntimeError as e:
    print 'ERROR:', e
    print agent_host.getUsage()
    exit(1)
if agent_host.receivedArgument("help"):
    print agent_host.getUsage()
    exit(0)

my_mission = MalmoPython.MissionSpec(missionXML, True)
my_mission_record = MalmoPython.MissionRecordSpec()

# Attempt to start a mission:
max_retries = 3
for retry in range(max_retries):
    try:
        agent_host.startMission(my_mission, my_mission_record)
        break
    except RuntimeError as e:
        if retry == max_retries - 1:
            print "Error starting mission:", e
            exit(1)
        else:
            time.sleep(2)

# Loop until mission starts:
print "Waiting for the mission to start ",
world_state = agent_host.getWorldState()
while not world_state.has_mission_begun:
    sys.stdout.write(".")
    time.sleep(0.1)
    world_state = agent_host.getWorldState()
    for error in world_state.errors:
        print "Error:", error.text

print
print "Mission running ",

start_time = time.time()
c_time = 0
firstWaypoint = None
ac = Controller(agent_host)
ac.setYaw(0)
nav = Navigator(ac)
sm = StateMachine()

sm.addState("explore")
c_time_threshold_explore = 4


def sm_explore_action():
    global firstWaypoint
    global c_time_threshold_explore
    if firstWaypoint is None:
        firstWaypoint = nav.lastWaypoint
    agent_host.sendCommand("move 1")
    if c_time > c_time_threshold_explore:
        ac.turnByAngle(90)
        c_time_threshold_explore += 4


def sm_explore_event():
    global nav
    nav.exploring = True


sm.addTransition("start", "explore", lambda: True, sm_explore_event)
sm.actions["explore"] = sm_explore_action

sm.addState("search")


def sm_search_event():
    global nav
    global agent_host
    nav.exploring = False
    agent_host.sendCommand("move 0")
    route = findRoute(nav.lastWaypoint, firstWaypoint)
    print route
    nav.setRoute(route)


def sm_nav_condition():
    global c_time
    return c_time >= 20.0


sm.addTransition("explore", "search", sm_nav_condition, sm_search_event)

sm.addState("navigating")
sm.addTransition("search", "navigating", lambda: not nav.exploring, lambda: True)


def sm_nav2start_event():
    print "target reached"
    global start_time
    start_time = time.time()


sm.addTransition("navigating", "start", lambda: nav.targetReached, sm_nav2start_event)

# Loop until mission ends:
while world_state.is_mission_running:
    time.sleep(0.05)
    c_time = time.time() - start_time

    world_state = agent_host.getWorldState()
    for error in world_state.errors:
        print "Error:", error.text
    if world_state.number_of_observations_since_last_state > 0:  # Have any observations come in?
        msg = world_state.observations[-1].text  # Yes, so get the text
        obs = json.loads(msg)
        if obs is not None:
            ac.update(obs)  # update controller
            nav.update()  # update navigation
            sm.update()  # update state machine

print
print "Mission ended"
# Mission has ended.
