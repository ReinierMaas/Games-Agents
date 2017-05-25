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

# This example shows how to use deal with basic waypoints
# You can create a graph, and find the shortest path to specific waypoints or those with specific flags

import MalmoPython
import os
import sys
import time
from controller import *
from navigation import *

sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)  # flush print output immediately


# Create default Malmo objects:

agent_host = MalmoPython.AgentHost()

#do stuff

controller = Controller(agent_host)
navigator = Navigator(controller)
# 7 - 8
# 3 4 5 6
# 1 2
wp1 = WaypointNode((0,0,0), 4)
wp2 = WaypointNode((1,0,0), 4)
wp3 = WaypointNode((0,1,0), 4)
wp4 = WaypointNode((1,1,0), 4)
wp5 = WaypointNode((2,1,0), 4)
wp6 = WaypointNode((3,1,0), 4)
wp7 = WaypointNode((1,2,0), 4)
wp8 = WaypointNode((2,2,0), 4)
wp1.assignNeighbor(wp2)
wp1.assignNeighbor(wp3)
wp4.assignNeighbor(wp3)
wp4.assignNeighbor(wp2)
wp5.assignNeighbor(wp4)
wp6.assignNeighbor(wp5)
wp7.assignNeighbor(wp3)
wp8.assignNeighbor(wp5)
wp8.data["tree"] = True
wp7.data["tree"] = True

print "7 - 8"
print "3 4 5 6"
print "1 2"
print "tree at 7 and 8"
print "route 1->6"
route = findRoute(wp1, wp6)
print map(lambda wp: wp.location, route)

print "route 1-> key = tree"
route = findRouteByKey(wp1, "tree")
print map(lambda wp: wp.location, route)

print "all routes 1-> key = tree"
routes = findRoutesByKey(wp1, "tree")
print map(lambda route: map(lambda wp: wp.location, route), routes)

print
print "Mission ended"
# Mission has ended.