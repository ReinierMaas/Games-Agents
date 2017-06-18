import numpy as np
import heapq
import time
import sys

'''
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
'''


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
    nav.findAndSet('log')
    print 'finding trees! find find...'
    return ActionReturn.success


def chopWood(w):
    ac = w["agentController"]
    nav = ac.navigator

    if "chopWood" not in w:
        w["chopWood"] = False

    if not w["chopWood"]:
        w["chopWood"] = True
        w["foundTree"] = False
        nav.findAndSet('log')
        ActionReturn.retry
    elif not w["foundTree"]:
        if nav.targetReached:
            w["foundTree"] = True
    else:
        if ac.destroyBlock('log'):
            ActionReturn.retry
        else:
            w["foundTree"] = False
            w["chopWood"] = False
            ActionReturn.success

    print 'chopping wood! chop chop...'
    return ActionReturn.success


def craftTable(w):
    w["agentController"].craft("crafting_table")
    print 'crafting crafting table! table...'
    return ActionReturn.success


def craftPlank(w):
    w["agentController"].craft("planks")
    print 'crafting planks! plank plank...'
    return ActionReturn.success


def craftSticks(w):
    w["agentController"].craft("stick")
    print 'crafting sticks! stick stick...'
    return ActionReturn.success


def craftHoe(w):
    w["agentController"].craft("wooden_hoe")
    print 'crafting hoe! hoe hoe...'
    return ActionReturn.success


def harvestGrain(w):
    print 'harvesting grain! oh no! there are is no grain, so I will plant some and check on them later'
    return ActionReturn.failure(5)


def bakeBread(w):
    print 'baking bread! bake bake...'
    return ActionReturn.success


# dijkstra's algorithm using priority queues
def pathfind(goals, actions, startstate, bannedset):
    root = Node(startstate, None, None)

    leafs = []  # priority queue of leafs
    heapq.heappush(leafs, (0, Leaf(None, root, bannedset)))

    debug_node_expansions = 0

    while leafs:  # while not empty
        if debug_node_expansions>=10000:
            print 'reached max node expantions: %d' % debug_node_expansions
            sys.exit()
        debug_node_expansions += 1
        (cost, leaf) = heapq.heappop(leafs)
        for goal in goals:
            if (goal.met(leaf.node.state)):
                print 'node expansions %d' % debug_node_expansions
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
    goals = np.array([
        Goal({'bread':1}),
    ])
    actions = np.array([
        Action("craftTable", craftTable, {'planks': 4}, {'tables': 1, 'planks': -4}),
        Action("craftPlank", craftPlank, {'logs': 1}, {'planks': 4, 'logs': -1}),
        Action("chopWood", chopWood, {}, {'logs': 1}),
        Action("craftHoe", craftHoe, {'tables': 1, 'planks': 2, 'sticks': 2}, {'hoes': 1, 'planks': -2, 'sticks': -2}),
        Action("craftSticks", craftSticks, {'planks': 2}, {'sticks': 4, 'planks': -1}),
        Action("harvestGrain", harvestGrain, {'hoes':1}, {'grain': 1}),
        Action("bakeBread", bakeBread, {'tables': 1, 'grain': 3}, {'bread':1, 'grain':-3}),
    ])
    print 'starting goap'
    starttime = time.time()
    leaf = pathfind(goals, actions, startstate, bannedSet)
    endtime = time.time()
    print 'done in %0.3f seconds' % (endtime - starttime)
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

class Actor:
    def __init__(self):
        self.state = {}    # dictionary of (mostly) ints
        self.timeouts = [] # array of ActionTimeouts
        self.plan = [] # array of Actions


if __name__ == '__main__':
    actors = [Actor()]
    for i in range(0,32): # simulate multiple frames (debug)
        print '--- FRAME %d ---' % i
        for actor in actors:
            # first we check out which items are currently banned
            currentTime = time.time()
            actor.timeouts = [timeout for timeout in actor.timeouts if not timeout.timeout<currentTime]
            banned = set([timeout.action for timeout in actor.timeouts])
            # check if we have to replan
            if actor.plan == []:
                actor.plan = plan(actor.state, banned)
            # then perform the action if there is a goal
            if actor.plan != []:
                action = actor.plan[0]
                result = action.function(None)
                if result == ActionReturn.retry:
                    continue
                elif result == ActionReturn.success:
                    del(actor.plan[0])
                elif result > 0:
                    # invalidate current plan and add current action to timeout
                    actor.plan = [] 
                    actor.timeouts.append(ActionTimeout(action, time.time()+result))
            else:
                print 'idling...'
        time.sleep(1)

