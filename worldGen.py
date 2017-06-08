def getTreeDecorator():
	return \
	"""<DrawingDecorator>
		<DrawSphere x="-5" y="11" z="0" radius="3" type="leaves" />
		<DrawLine x1="-5" y1="7" z1="0" x2="-5" y2="11" z2="0" type="log" />
		<DrawLine x1="-6" y1="7" z1="-1" x2="-6" y2="7" z2="1" type="stone" />
		<DrawLine x1="-6" y1="8" z1="-1" x2="-6" y2="8" z2="1" type="glass" />
	</DrawingDecorator>"""

def getFlatWorldGenerator():
	return """<FlatWorldGenerator generatorString="3;7,5*3,2;1;" forceReset="true" />"""

def getMissionXML(generator, drawingDecorator, cubeObs = "cube10", cubeSize = 2, startLocationAndAngles = (1.5, 7.0, 13.5,90,10), \
	gameMode = "Survival", startTime = 10000, weather = "clear", timeLimit = 60000):
	""" Generates mission XML with flat world and 1 crappy tree. """
	x,y,z,yaw,pitch = startLocationAndAngles
	return """<?xml version="1.0" encoding="UTF-8" ?>
		<Mission xmlns="http://ProjectMalmo.microsoft.com" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
			<About>
				<Summary>Games and Agents project</Summary>
			</About>

			<ServerSection>
				<ServerInitialConditions>
					<Time>
						<StartTime>{startTime}</StartTime>
						<AllowPassageOfTime>true</AllowPassageOfTime>
					</Time>

					<Weather>{weather}</Weather>
				</ServerInitialConditions>

				<ServerHandlers>
					{generator}
					{drawingDecorator}
					<ServerQuitWhenAnyAgentFinishes />
					<ServerQuitFromTimeUp timeLimitMs="{timeLimit}" description="Ran out of time." />
				</ServerHandlers>
			</ServerSection>

			<AgentSection mode="{gameMode}">
				<Name>YourMom</Name>
				<AgentStart>
					<Placement x="{startX}" y="{startY}" z="{startZ}" yaw="{startYaw}" pitch="{startPitch}" />
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
		</Mission>""".format(cubeObs, cubeSize, generator = generator, \
			weather = weather, timeLimit = timeLimit, gameMode = gameMode, \
			startX = x, startY = y, startZ = z, startYaw = yaw, startPitch = pitch, \
			startTime = startTime, drawingDecorator = drawingDecorator)
