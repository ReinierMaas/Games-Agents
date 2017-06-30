import numpy as np
import heapq
import time
import sys

from util import *

"""
Okay, there are three levels of complexity we can choose
simplest: use boolean state
		  - library does this
medium:   use integer state
		  - we probbably want this
		  - requires modifying library
			> actually, throwing lib away was easier
		  - requires different A* heuristic
			> none, just be Dijkstra
			  bad heuristic is worse than no heuristic,
			  bad heuristic can also result in sub-optimal paths
complex:  use custom state with user-supplied functions and heuristic
		  - probbably overkill
		  - requires rewriting library
		  - requires custom functions for each action
		  - requires complex A* heuristic
"""


FOUND_TREE = "foundTree"
FOUND_GRASS = "foundGrass"
FOUND_WHEAT = "foundWheat"

CHOP_WOOD = "chopWood"
GET_SEEDS = "getSeeds"
GET_WHEAT = "getWheat"


class Goal:
	def __init__(self, state):
		self.state = state  # int dict

	def met(self, teststate):
		for (key, value) in self.state.iteritems():
			if (teststate.get(key, 0) < value):
				return False
		return True


class Action:
	def __repr__(self):
		return self.name

	def __init__(self, name, function, condition, expectation, cost=1):
		self.name = name
		self.function = function  # function
		self.condition = condition  # int dict
		self.expectation = expectation  # int dict
		self.cost = cost  # int

	def available(self, state):
		for (key, value) in self.condition.iteritems():
			if (state.get(key, 0) < value):
				return False
		return True


class Node:
	def __repr__(self):
		return "\n(a{0}|{1})".format(self.state, self.prev)

	def __init__(self, state, prev, action):
		self.state = state  # int dict
		self.prev = prev  # Node
		self.action = action  # Action


class Leaf:
	def __repr__(self):
		return "leaf {0} {1} {2}\n".format(self.prevAction, list(self.doneActions), self.node)

	def __init__(self, prevAction, node, aset):
		self.prevAction = prevAction
		self.node = node  # Node
		self.doneActions = aset  # int set


def addDict(a, b):
	ret = {}
	for key in a:
		ret[key] = a.get(key, 0) + b.get(key, 0)
	for key in b:
		ret[key] = a.get(key, 0) + b.get(key, 0)
	return ret

# python 2.7 enum
class ActionReturn:
	success, replanWithoutMe = range(2)
	success =  0 # action was completed without issues
	retry   = -1 # retry action next simulation-tick
	@staticmethod
	def failure(secondsTimeout=10): # failure, replan and don't reconsider action until timeout
		return secondsTimeout

def findTrees(w):
	ac = w["agentController"]
	nav = ac.navigator
	nav.findAndSet(BLOCK_WOOD)
	print "<Agent{}> finding trees! find find...".format(w["id"])
	return ActionReturn.success


def chopWood(w):
	if w is None:
		print "goap.py:chopWood(w): w is None"
		return ActionReturn.failure()

	ac = w["agentController"]

	if ac is None:
		print "goap.py:chopWood(w): ac is None"
		return ActionReturn.failure()

	nav = ac.navigator

	if nav is None:
		print "goap.py:chopWood(w): nav is None"
		return ActionReturn.failure()

	if CHOP_WOOD not in w:
		w[CHOP_WOOD] = False

	print "<Agent{}> chopping wood! chop chop...".format(w["id"])

	if not w[CHOP_WOOD]:
		w[CHOP_WOOD] = True
		w[FOUND_TREE] = False
		print "filters = {}".format(w["filters"])
		destination = nav.findAndSet(BLOCK_WOOD, w["id"], w["filters"])

		if destination is None:
			print "goap.py:chopWood(w):nav.findAndSet(...) destination is None"
			return ActionReturn.failure()

		w["destination"] = destination
		return ActionReturn.retry
	elif not w[FOUND_TREE]:
		if nav.targetReached:
			w[FOUND_TREE] = True
	else:
		tempDestination = w["destination"]

		if w["destination"] is None:
			print "goap.py:chopWood(w):w[\"destination\"] is None"
			# return ActionReturn.failure()
		else:
			tempDestination = tempDestination.location

		print "CHOPPING WOOD!"

		if ac.destroyBlock(BLOCK_WOOD, tempDestination):
			return ActionReturn.retry
		else:
			w[FOUND_TREE] = False
			w[CHOP_WOOD] = False

			if w["destination"] is not None:
				w["destination"].removeFlag(w["id"])
				w["destination"].removeFlag(BLOCK_WOOD)
				ac.controller.setPitch(-10)
				w["destination"] = None
				return ActionReturn.success
			else:
				print "goap, w[destination] is None"
				return ActionReturn.failure()

	return ActionReturn.success

def getSeeds(w):
	if w is None:
		print "goap.py:getSeeds(w): w is None"
		return ActionReturn.failure()

	ac = w["agentController"]

	if ac is None:
		print "goap.py:getSeeds(w): ac is None"
		return ActionReturn.failure()

	nav = ac.navigator

	if nav is None:
		print "goap.py:getSeeds(w): nav is None"
		return ActionReturn.failure()

	if GET_SEEDS not in w:
		w[GET_SEEDS] = False

	print "<Agent{}> Getting seeds! ...".format(w["id"])

	if not w[GET_SEEDS]:
		w[GET_SEEDS] = True
		w[FOUND_GRASS] = False
		print "filters = {}".format(w["filters"])
		destination = nav.findAndSet(BLOCK_TALL_GRASS, w["id"], w["filters"])

		if destination is None:
			print "goap.py:getSeeds(w):nav.findAndSet(...) destination is None"
			return ActionReturn.failure()

		w["destination"] = destination
		return ActionReturn.retry

	elif not w[FOUND_GRASS]:
		if nav.targetReached:
			w[FOUND_GRASS] = True
	else:
		tempDestination = w["destination"]

		if w["destination"] is None:
			print "goap.py:getSeeds(w):w[\"destination\"] is None"
			# return ActionReturn.failure()
		else:
			tempDestination = tempDestination.location

		print "GETTING SEEDS!"
		if ac.destroyBlock(BLOCK_TALL_GRASS, tempDestination):
			return ActionReturn.retry
		else:
			w[FOUND_GRASS] = False
			w[GET_SEEDS] = False

			if w["destination"] is not None:
				w["destination"].removeFlag(w["id"])
				w["destination"].removeFlag(BLOCK_TALL_GRASS)
				ac.controller.setPitch(-10)
				w["destination"] = None
				return ActionReturn.success
			else:
				print "goap, w[destination] is None"
				return ActionReturn.failure()

	return ActionReturn.success

def craftTable(w):
	w["agentController"].craft("crafting_table")
	print "<Agent{}> crafting crafting table! table...".format(w["id"])
	return ActionReturn.success


def craftPlank(w):
	w["agentController"].craft("planks")
	print "<Agent{}> crafting planks! plank plank...".format(w["id"])
	return ActionReturn.success


def craftSticks(w):
	w["agentController"].craft("stick")
	print "<Agent{}> crafting sticks! stick stick...".format(w["id"])
	return ActionReturn.success


def craftHoe(w):
	w["agentController"].craft("wooden_hoe")
	print "<Agent{}> crafting hoe! hoe hoe...".format(w["id"])
	return ActionReturn.success

def harvestOrPlantWheat(w):
	if w is None:
		print "goap.py:harvestOrPlantWheat(w): w is None"
		return ActionReturn.failure()
	ac = w["agentController"]
	if ac is None:
		print "goap.py:harvestOrPlantWheat(w): ac is None"
		return ActionReturn.failure()
	nav = ac.navigator
	if nav is None:
		print "goap.py:harvestOrPlantWheat(w): nav is None"
		return ActionReturn.failure()

	if GET_WHEAT not in w:
		w[GET_WHEAT] = False
	print "<Agent{}> getting wheat! wheat wheat...".format(w["id"])

	if not w[GET_WHEAT]:
		w[GET_WHEAT] = True
		w[FOUND_WHEAT] = False
		destination = nav.findAndSet(BLOCK_WHEAT, w["id"], w["filters"])

		if destination is None:
			# No wheat available... plant some... look for grass first
			newDestination = nav.findAndSet(BLOCK_GRASS, w["id"], w["filters"])

			if newDestination is None:
				print "Well I give up, no wheat and no grass available??? :("
				print "returning shit: {}".format(ActionReturn.failure())
				return ActionReturn.failure()

			print "planting seeds at first grass position..."

			if nav.targetReached:
				hoeSlot = ac.inventoryHandler.getHotbarSlot("wooden_hoe")
				seedsSlot = ac.inventoryHandler.getHotbarSlot(SEEDS)
				success = ac.tileGrassAndPlantSeeds(newDestination.location, hoeSlot, seedsSlot)

				if not success:
					# Hopefully planted seeds...
					w["destination"] = newDestination

					if w["destination"] is not None:
						w["destination"].setFlag(w["id"])
						w["destination"].setFlag(BLOCK_TALL_GRASS)
						ac.controller.setPitch(-10)
						w["destination"] = None
						return ActionReturn.success
					else:
						print "goap, w[destination] is None"
						return ActionReturn.failure()
					pass
				else:
					# Continue/Try again later...
					pass

			return ActionReturn.retry

		w["destination"] = destination
		return ActionReturn.retry
	elif not w[FOUND_WHEAT]:
		if nav.targetReached:
			w[FOUND_WHEAT] = True
	else:
		if w["destination"] is None:
			print "goap.py:harvestOrPlantWheat(w):w[\"destination\"] is None"
			return ActionReturn.failure()
		if ac.harvestCrop(w["destination"].location, BLOCK_WHEAT):
			return ActionReturn.retry
		else:
			w[FOUND_WHEAT] = False
			w[GET_WHEAT] = False
			if w["destination"] is not None:
				w["destination"].removeFlag(w["id"])
				w["destination"].removeFlag(BLOCK_WHEAT)
				ac.controller.setPitch(-10)
				w["destination"] = None
				return ActionReturn.success
			else:
				print "goap, w[destination] is None"
				return ActionReturn.failure()

	return ActionReturn.success
	print "<Agent{}> harvesting Wheat! oh no! there is no Wheat, so I will plant some and check on them later".format(w["id"])



def bakeBread(w):
	print "<Agent{}> baking bread! bake bake...".format(w["id"])

	# Check if we have sufficient wheat to craft bread...
	if w["agentController"].inventoryHandler.getItemAmount("wheat") >= 3:
		w["agentController"].craft("bread")
		return ActionReturn.success
	else:
		return ActionReturn.failure()



# dijkstra"s algorithm using priority queues
def pathfind(goals, actions, startstate, bannedset):
	root = Node(startstate, None, None)

	leafs = []  # priority queue of leafs
	heapq.heappush(leafs, (0, Leaf(None, root, bannedset)))

	debugNodeExpansions = 0

	while leafs:  # while not empty
		if debugNodeExpansions>=10000:
			print "reached max node expansions: %d" % debugNodeExpansions
			break
		debugNodeExpansions += 1
		(cost, leaf) = heapq.heappop(leafs)
		for goal in goals:
			if (goal.met(leaf.node.state)):
				print "node expansions %d" % debugNodeExpansions
				print leaf
				return leaf
		for action in actions:
			if action.available(leaf.node.state) and (action == leaf.prevAction or action not in leaf.doneActions):
				aset = leaf.doneActions.copy()
				aset.add(action)
				node = Node(addDict(leaf.node.state, action.expectation), leaf.node, action)
				heapq.heappush(leafs, (cost + action.cost, Leaf(action, node, aset)))
	return Leaf(0, root, bannedset)

# simple wrapper around pathfind to make it easier to use
def plan(startstate, bannedSet):
	# Default goals of an agent
	goals = np.array([
		Goal({"bread":1}),
	])

	# Default list of actions that an agent can do
	actions = np.array([
		Action("craftTable", craftTable, {"planks": 4}, {"crafting_table": 1, "planks": -4}),
		Action("craftPlank", craftPlank, {"logs": 1}, {"planks": 4, "logs": -1}),
		Action(CHOP_WOOD, chopWood, {}, {"logs": 1}),
		Action(GET_SEEDS, getSeeds, {}, {SEEDS: 1}),
		Action("craftHoe", craftHoe, {"crafting_table": 1, "planks": 2, "sticks": 2}, {"wooden_hoe": 1, "planks": -2, "sticks": -2}),
		Action("craftSticks", craftSticks, {"planks": 2}, {"sticks": 4, "planks": -1}),
		Action("harvestOrPlantWheat", harvestOrPlantWheat, {"wooden_hoe": 1, SEEDS: 1}, {"wheat": 1, SEEDS: -1}),
		Action("bakeBread", bakeBread, {"crafting_table": 1, "wheat": 3}, {"bread": 1, "wheat": -3}),
	])

	print "starting goap"
	starttime = time.time()
	leaf = pathfind(goals, actions, startstate, bannedSet)
	endtime = time.time()
	print "done in %0.3f seconds" % (endtime - starttime)
	node = leaf.node
	path = []
	while node != None:
		if (node.action != None):
			path.append(node.action)
		node = node.prev
	# reversed(list) does not reverse the list, but give you a special iterator
	# so I'm using this funky syntax to _actually_ reverse the list
	return path[::-1]

class ActionTimeout:
	def __init__(self, action, timeout):
		self.action = action
		self.timeout = timeout

class Goap:
	def __init__(self, agentController, agentId, agentCount):
		self.meta = {}
		self.meta["agentController"] = agentController
		self.meta["id"] = agentId
		self.meta["filters"] = [i + 1 if i >= agentId else i for i in range(agentCount - 1)]
		self.state = {} # dictionary of ints
		self.timeouts = [] # array of ActionTimeouts
		self.plan = [] # array of Actions

	def updateState(self):
		self.state = self.meta["agentController"].inventoryHandler.getCombinedDict()

	def execute(self):
		# first we check out which items are currently banned
		currentTime = time.time()
		self.timeouts = [timeout for timeout in self.timeouts if not timeout.timeout<currentTime]
		banned = set([timeout.action for timeout in self.timeouts])
		# check if we have to replan
		if self.plan == []:
			self.plan = plan(self.state, banned)
		# then perform the action if there is a goal
		if self.plan != []:
			# print "plan = {}".format(self.plan)
			# print "state = {}".format(self.state)

			action = self.plan[0]
			result = action.function(self.meta)
			if result == ActionReturn.retry:
				return
			elif result == ActionReturn.success:
				del(self.plan[0])
			elif result > 0:
				# invalidate current plan and add current action to timeout
				self.plan = []
				self.timeouts.append(ActionTimeout(action, time.time() + result))
		else:
			print "idling..."


if __name__ == "__main__":
	goapInstance = Goap(None)
	goapInstance.execute()

