import numpy as np
import heapq
import time

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
        self.state = state # int dict
    def met(self, teststate):
        for (key, value) in self.state.iteritems():
            if(teststate.get(key, 0)<value):
                return False
        return True

class Action:
    def __repr__(self):
        return self.name
    def __init__(self, name, action, condition, expectation, cost=1):
        self.name       = name
        self.action     = action # Action
        self.condition  = condition  # int dict
        self.expectation = expectation # int dict
        self.cost       = cost # int
    def available(self, state):
        for (key, value) in self.condition.iteritems():
            if(state.get(key, 0)<value):
                return False
        return True

class Node:
    def __repr__(self):
        return "\n(a{1} s{0}|{2})".format(self.state, list(self.doneActions), self.prev)
    def __init__(self, state, prev, action, aset):
        self.state=state # int dict
        self.prev=prev # Node
        self.action=action # Action
        self.doneActions=aset# int set

class Leaf:
    def __repr__(self):
        return "leaf {0} {1}\n".format(self.prevAction, self.node)
    def __init__(self, prevAction, node):
        self.prevAction=prevAction
        self.node=node # Node

def addDict(a, b):
    ret = {}
    for key in a:
        ret[key] = a.get(key,0) + b.get(key,0)
    for key in b:
        ret[key] = a.get(key,0) + b.get(key,0)
    return ret

# dijkstra's algorithm using priority queues
def pathfind(goals, actions, startstate):
    root = Node(startstate, None, None, set())

    leafs = [] # priority queue of leafs
    heapq.heappush(leafs, (0, Leaf(None, root)))

    nodeexpantions = 0

    while leafs: # while not empty
        nodeexpantions+=1
        (cost, leaf) = heapq.heappop(leafs)
        for goal in goals:
            if(goal.met(leaf.node.state)):
                print 'node expantions: %d' % nodeexpantions
                print leaf
                return leaf
        for action in actions:
            if action.available(leaf.node.state) and (action == leaf.prevAction or action not in leaf.node.doneActions):
                aset = leaf.node.doneActions.copy()
                aset.add(action)
                node = Node(addDict(leaf.node.state,action.expectation), leaf.node, action, aset)
                heapq.heappush(leafs, (cost+action.cost, Leaf(action, node)))
    return Leaf(0, root)

# simple wrapper around pathfind to make it easier to use
def plan(goals, actions, startstate):
    print 'starting'
    starttime = time.time()
    leaf = pathfind(goals, actions, state)
    endtime = time.time()
    print 'done in %0.3f seconds' % (endtime-starttime)
    node = leaf.node
    path = []
    while node != None:
        if(node.action != None):
            path.append(node.action)
        node = node.prev
    return reversed(path)

def findTrees(w):
    print 'finding trees! find find...'

def chopWood(w):
    print 'chopping wood! chop chop...'

def craftTable(w):
    print 'crafting crafting table! table...'

def craftPlank(w):
    print 'crafting planks! plank plank...'

def craftSticks(w):
    print 'crafting sticks! stick stick...'

def craftHoe(w):
    print 'crafting hoe! ho ho...'

if __name__ == '__main__':
    goals = np.array([
        Goal({'hoes':1}),
        ])
    actions = np.array([
        Action("findTrees", findTrees,  {},           {'trees':1}),
        Action("craftTable", craftTable, {'planks':4}, {'tables':1, 'planks':-4}),
        Action("craftPlank", craftPlank, {'logs':1},   {'planks':4, 'logs':-1}),
        Action("chopWood", chopWood,   {'trees':1},  {'trees':-1, 'logs':1}),
        Action("craftHoe", craftHoe,   {'tables':1, 'planks':2, 'sticks':2}, {'hoes':1,'planks':-2,'sticks':-2}),
        Action("craftSticks", craftSticks,{'planks':2}, {'sticks':4, 'planks':-1}),
        ])
    state = {}
    path = plan(goals, actions, state)
    for action in path:
        action.action(None)

