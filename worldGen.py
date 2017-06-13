import random

def getTreeDecorator():
	return \
	"""<DrawingDecorator>
		<DrawSphere x="-5" y="11" z="0" radius="3" type="leaves" />
		<DrawLine x1="-5" y1="7" z1="0" x2="-5" y2="11" z2="0" type="log" />
		<DrawLine x1="-6" y1="7" z1="-1" x2="-6" y2="7" z2="1" type="stone" />
		<DrawLine x1="-6" y1="8" z1="-1" x2="-6" y2="8" z2="1" type="glass" />
	</DrawingDecorator>"""


def makeDecorator(commands):
	return   """<DrawingDecorator>{}</DrawingDecorator>""".format(''.join(commands))

def makeTree(x,y,z):
	return 	'''
			<DrawSphere x="{x}" y="{y4}" z="{z}" radius="3" type="leaves" />
			<DrawLine x1="{x}" y1="{y}" z1="{z}" x2="{x}" y2="{y4}" z2="{z}" type="log" />
			'''.format(x = x, y = y, y4 = y + 4, z = z)

def makeLake(x,z,w,d):
	return 	'''
			<DrawCuboid x1="{x1}" y1="{y1}" z1="{z1}" x2 = "{x2}" y2 = "{y2}" z2 = "{z2}" type="water" />
			<DrawCuboid x1="{x1}" y1="{y3}" z1="{z1}" x2 = "{x2}" y2 = "{y3}" z2 = "{z2}" type="air" />
			'''.format(x1 = x, x2 = x + (w-1), y1 = 6, y2 = 5, y3 = 7, z1 = z, z2 = z + (d-1))

def makeGrass(x,y,z,w,d):
	return '''
			<DrawCuboid x1="{x1}" y1="{y1}" z1="{z1}" x2 = "{x2}" y2 = "{y2}" z2 = "{z2}" type="tallgrass" />
			'''.format(x1 = x, x2 = x + (w-1), y1 = y, y2 = y, z1 = z, z2 = z + (d-1))

def setSeed(seed):
	random.setSeed(seed)

def genLakes():
	lakes = []
	lakeLocs = []
	for ix in range(-5, 5):
		for iz in range(-5, 5):
			rng = random.randint(0, 5)
			if rng == 1:
				rngCenter = [random.randint(2,10), random.randint(2,10)]
				xcenter, zcenter = rngCenter[0] + ix * 20, rngCenter[1] + iz * 20
				w1 = random.randint(4, 20 - abs(10 - rngCenter[0]))
				d1 = random.randint(4, 20 - abs(10 - rngCenter[1]))
				w2 = random.randint(4, 20 - abs(10 - rngCenter[0]))
				d2 = random.randint(4, 20 - abs(10 - rngCenter[1]))
				x1, z1 = xcenter - w1/2, zcenter - d1/2
				x2, z2 = xcenter - w2/2, zcenter - d2/2
				lakes.append(makeLake(x1, z1, w1, d1))
				lakeLocs.append((x1,z1,w1,d1))
				lakes.append(makeLake(x2, z2, w2, d2))
				lakeLocs.append((x2,z2,w2,d2))
	#add boundaries
	lakes.append(makeLake(-150, -150, 10, 300))
	lakeLocs.append((-150, -150, 10, 300))
	lakes.append(makeLake(140, -150, 10, 300))
	lakeLocs.append((140, -150, 10, 300))
	lakes.append(makeLake(-150, -150, 300, 10))
	lakeLocs.append((-150, -150, 300, 10))
	lakes.append(makeLake(-150, 140, 300, 10))
	lakeLocs.append((-150, 140, 300, 10))
	return lakes, lakeLocs

def genGrass():
	grass = []
	for ix in range(-20, 20):
		for iz in range(-20, 20):
			rng = random.randint(0,5)
			if rng == 1:
				rng2 = random.randint(3,7)
				rng3 = random.randint(3,7)
				x, z = ix * 5, iz * 5
				grass.append(makeGrass(x, 7, z, rng2, rng3))
	return grass

def genTrees():
	trees = []
	locs = []
	for ix in range(-10, 10):
		for iz in range(-10, 10):
			rng = random.randint(0,2)
			if rng == 1:
				x, z = ix * 10, iz * 10
				trees.append(makeTree(x,7,z))
				locs.append((x,z))
	return trees, locs

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
