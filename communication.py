import goap
import json
import MalmoPython
import sys
import os
import time
import uuid
import random
from collections import namedtuple
from agentController import *

class Agent:
    def __init__(self, agentID, location, host, mission, missionRecord):
        self.agentID = agentID  # int
        self.location = location  # (float, float, float)
        self.goap = None # goap class
        self.currentPlan = []  # Action list
        self.messageCounter = 0  # messages sent by the agent
        self.agentHost = host
        self.missionRecordSpec = missionRecord
        self.missionSpec = mission
        self.agentController = AgentController(host)

    def sendQuery(self, content):
        ret = json.dump({'type': 'Q',
                         'senderID': self.agentID,
                         'messageNr': self.messageCounter,
                         'senderLocation': self.location,
                         'content': content})
        self.messageCounter += 1
        return ret

    def sendReply(self, recipientID, replyToID, content):
        ret = json.dump({'type': 'R',
                         'senderID': self.agentID,
                         'messageNr': self.messageCounter,
                         'senderLocation': self.location,
                         'recipientID': recipientID,
                         'replyToID': replyToID,
                         'content': content})
        self.messageCounter += 1
        return ret

    def sendConfirmation(self, recipientID, confirmToID, content):
        ret = json.dump({'type': 'C',
                         'senderID': self.agentID,
                         'messageNr': self.messageCounter,
                         'senderLocation': self.location,
                         'recipientID': recipientID,
                         'confirmToID': confirmToID,
                         'content': content})
        self.messageCounter += 1
        return ret

    def startMission(self, client_pool):
        max_retries = 3
        for retry in range(max_retries):
            try:
                # Attempt to start the mission:
                self.agentHost.startMission(self.missionSpec, client_pool, self.missionRecordSpec, self.agentID,
                                            "neejij")

                break
            except RuntimeError as e:
                if retry == max_retries - 1:
                    print "Error starting mission", e
                    print "Is the game running?"
                    exit(1)
                else:
                    # In a multi-agent mission, startMission will fail if the integrated server
                    # hasn't yet started - so if none of our clients were available, that may be the
                    # reason. To catch this specifically we could check the results for "MALMONOSERVERYET",
                    # but it should be sufficient to simply wait a bit and try again.
                    time.sleep(5)


if __name__ == '__main__':
    EntityInfo = namedtuple('EntityInfo', 'x, y, z, yaw, pitch, name, colour, variation, quantity')
    EntityInfo.__new__.__defaults__ = (0, 0, 0, 0, 0, "", "", "", 1)


    def getXML(reset):
        # Set up the Mission XML:
        xml = '''<?xml version="1.0" encoding="UTF-8" standalone="no" ?>
        <Mission xmlns="http://ProjectMalmo.microsoft.com" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
          <About>
            <Summary/>
          </About>

          <ServerSection>
            <ServerInitialConditions>
              <Time>
                <StartTime>13000</StartTime>
              </Time>
            </ServerInitialConditions>
            <ServerHandlers>
              <FlatWorldGenerator forceReset="''' + reset + '''" generatorString="3;2*4,225*22;1;" seed=""/>
              <DrawingDecorator>
                <DrawCuboid x1="-20" y1="200" z1="-20" x2="20" y2="200" z2="20" type="glowstone"/>
                <DrawCuboid x1="-19" y1="200" z1="-19" x2="19" y2="227" z2="19" type="stained_glass" colour="RED"/>
                <DrawCuboid x1="-18" y1="202" z1="-18" x2="18" y2="247" z2="18" type="air"/>
              </DrawingDecorator>
              <ServerQuitFromTimeUp description="" timeLimitMs="50000"/>
            </ServerHandlers>
          </ServerSection>
        '''

        # Add an agent section for each robot. Robots run in survival mode.
        # Give each one a wooden pickaxe for protection...

        for i in xrange(NUM_AGENTS):
            xml += '''<AgentSection mode="Survival">
            <Name>''' + str(i) + '''</Name>
            <AgentStart>
              <Placement x="''' + str(random.randint(-17, 17)) + '''" y="204" z="''' + str(random.randint(-17, 17)) + '''"/>
              <Inventory>
                <InventoryObject type="wooden_pickaxe" slot="0" quantity="1"/>
              </Inventory>
            </AgentStart>
            <AgentHandlers>
              <ContinuousMovementCommands turnSpeedDegs="360"/>
              <ChatCommands/>
              <MissionQuitCommands/>
              <RewardForCollectingItem>
                <Item type="apple" reward="1"/>
              </RewardForCollectingItem>
              <ObservationFromNearbyEntities>
                <Range name="entities" xrange="40" yrange="2" zrange="40"/>
              </ObservationFromNearbyEntities>
              <ObservationFromRay/>
              <ObservationFromFullStats/>
            </AgentHandlers>
          </AgentSection>'''

        # Add a section for the observer. Observer runs in creative mode.

        xml += '''<AgentSection mode="Creative">
            <Name>TheWatcher</Name>
            <AgentStart>
              <Placement x="0.5" y="228" z="0.5" pitch="90"/>
            </AgentStart>
            <AgentHandlers>
              <ContinuousMovementCommands turnSpeedDegs="360"/>
              <MissionQuitCommands/>
              <VideoProducer>
                <Width>640</Width>
                <Height>640</Height>
              </VideoProducer>
            </AgentHandlers>
          </AgentSection>'''

        xml += '</Mission>'
        return xml


    # More interesting generator string: "3;7,44*49,73,35:1,159:4,95:13,35:13,159:11,95:10,159:14,159:6,35:6,95:6;12;"

    # missionXML = '''<?xml version="1.0" encoding="UTF-8" standalone="no" ?>
    #             <Mission xmlns="http://ProjectMalmo.microsoft.com" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    #
    #             <About>
    #                 <Summary>Hello world!</Summary>
    #             </About>
    #
    #             <ModSettings>
    #                 <MsPerTick>50</MsPerTick>
    #             </ModSettings>
    #
    #             <ServerSection>
    #             <ServerInitialConditions>
    #                 <Time>
    #                     <StartTime>13000</StartTime>
    #                 </Time>
    #             </ServerInitialConditions>
    #                 <ServerHandlers>
    #                     <FlatWorldGenerator generatorString="3;7,220*1,5*3,2;3;,biome_1"/>
    #                     <ServerQuitFromTimeUp timeLimitMs="3000000"/>
    #                 </ServerHandlers>
    #             </ServerSection>
    #
    #
    #             <AgentSection mode="Survival">
    #                 <Name>MalmoTutorialBot1</Name>
    #                 <AgentStart>
    #                     <Placement x="10" y="228" z="0"/>
    #                 </AgentStart>
    #
    #                 <AgentHandlers>
    #                     <ObservationFromFullStats/>
    #                     <ContinuousMovementCommands turnSpeedDegs="180"/>
    #                 </AgentHandlers>
    #             </AgentSection>
    #
    #             <AgentSection mode="Survival">
    #                 <Name>MalmoTutorialBot2</Name>
    #                 <AgentStart>
    #                     <Placement x="10" y="228" z="0"/>
    #                 </AgentStart>
    #                 <AgentHandlers>
    #                     <ObservationFromFullStats/>
    #                     <ContinuousMovementCommands turnSpeedDegs="180"/>
    #                 </AgentHandlers>
    #             </AgentSection>
    #
    #             <AgentSection mode="Survival">
    #                 <Name>MalmoTutorialBot3</Name>
    #                 <AgentStart>
    #                     <Placement x="10" y="228" z="0"/>
    #                 </AgentStart>
    #                 <AgentHandlers>
    #                     <ObservationFromFullStats/>
    #                     <ContinuousMovementCommands turnSpeedDegs="180"/>
    #                 </AgentHandlers>
    #             </AgentSection>
    #
    #
    #             <AgentSection mode="Creative">
    #                 <Name>TheWatcher</Name>
    #                 <AgentStart>
    #                     <Placement x="0.5" y="228" z="0.5" pitch="90"/>
    #                 </AgentStart>
    #                 <AgentHandlers>
    #                     <ContinuousMovementCommands turnSpeedDegs="360"/>
    #                     <MissionQuitCommands/>
    #                     <VideoProducer>
    #                         <Width>640</Width>
    #                         <Height>640</Height>
    #                     </VideoProducer>
    #                 </AgentHandlers>
    #             </AgentSection>
    #
    #             </Mission>
    #
    #             '''

    NUM_AGENTS = 4
    agents = []
    for i in range(NUM_AGENTS):
        agents.append(Agent(i,(0,0,0),{}))


    agent_hosts = [MalmoPython.AgentHost()]
    agent_hosts[0].addOptionalFlag("debug,d", "Display debug information.")
    agent_hosts[0].addOptionalIntArgument("agents,n", "Number of agents to use, including observer.", 4)

    try:
        agent_hosts[0].parse(sys.argv)
    except RuntimeError as e:
        print 'ERROR:', e
        print agent_hosts[0].getUsage()
        exit(1)
    if agent_hosts[0].receivedArgument("help"):
        print agent_hosts[0].getUsage()
        exit(0)

    DEBUG = agent_hosts[0].receivedArgument("debug")
    agents_requested = agent_hosts[0].getIntArgument("agents")
    NUM_AGENTS = max(1, agents_requested - 1)  # Will be NUM_AGENTS robots running around, plus one static observer.

    # for x in xrange(1, NUM_AGENTS + 1):
    #     agent_host = MalmoPython.AgentHost()
    #     agent_hosts += [ agent_host ]
    #     agents.append(Agent(x, (0,0,0), {}, missionXML=missionXML))

    agent_hosts += [MalmoPython.AgentHost() for x in xrange(1, NUM_AGENTS + 1)]

    # Set up debug output:
    for ah in agent_hosts:
        ah.setDebugOutput(DEBUG)  # Turn client-pool connection messages on/off.

    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)  # flush print output immediately

    # set up a client pool
    client_pool = MalmoPython.ClientPool()
    for x in xrange(10000, 10000 + NUM_AGENTS + 1):
        client_pool.add(MalmoPython.ClientInfo('127.0.0.1', x))


    def tut_startMission(agent_host, my_mission, my_client_pool, my_mission_record, role, expId):
        max_retries = 3
        for retry in range(max_retries):
            try:
                # Attempt to start the mission:
                agent_host.startMission(my_mission, my_client_pool, my_mission_record, role, expId)
                break
            except RuntimeError as e:
                if retry == max_retries - 1:
                    print "Error starting mission", e
                    print "Is the game running?"
                    exit(1)
                else:
                    # In a multi-agent mission, startMission will fail if the integrated server
                    # hasn't yet started - so if none of our clients were available, that may be the
                    # reason. To catch this specifically we could check the results for "MALMONOSERVERYET",
                    # but it should be sufficient to simply wait a bit and try again.
                    time.sleep(5)


    experimentID = str(uuid.uuid4())

    for i in range(len(agent_hosts)):
        tut_startMission(agent_hosts[i], MalmoPython.MissionSpec(getXML("false"), True), client_pool, MalmoPython.MissionRecordSpec(), i, experimentID)

    # Wait for mission to start - complicated by having multiple agent hosts, and the potential
    # for multiple errors to occur in the start-up process.


    # missionSpec = MalmoPython.MissionSpec(missionXML, True) # ?
    # missionRecordSpec = MalmoPython.MissionRecordSpec() # ?
    # agent_hosts[0].startMission(missionSpec, client_pool, missionRecordSpec, 0, "neejij")

    # for agent in agents:
    #     max_retries = 3
    #     for retry in range(max_retries):
    #         try:
    #             print agent.agentID
    #             agent.startMission(client_pool)
    #             break
    #         except RuntimeError as e:
    #             if retry == max_retries - 1:
    #                 print "Error starting mission:", e
    #                 exit(1)
    #             else:
    #                 time.sleep(2)
    #     agent.currentPlan = goap.plan(agent.goapState)
