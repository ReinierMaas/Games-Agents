import numpy as np
import heapq

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
              bad heuristic is worse than no heuristic, can also result in sub-optimal paths
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
    def __init__(self, action, condition, expectation, cost=1):
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
        return "({0}|{1})".format(self.state, self.prev)
    def __init__(self, state, prev, action):
        self.state=state # dictionary of integers
        self.prev=prev # pointer to Node
        self.action=action # pointer to action

class Leaf:
    def __repr__(self):
        return "leaf {0} {1}\n".format(self.cost, self.node)
    def __init__(self, cost, node):
        self.cost=cost # integer
        self.node=node # pointer to Node

def addDict(a, b):
    ret = {}
    for key in a:
        ret[key] = a.get(key,0) + b.get(key,0)
    for key in b:
        ret[key] = a.get(key,0) + b.get(key,0)
    return ret

# dijkstra's algorithm
def pathfind(goals, actions, startstate):
    root = Node(startstate, None, None)
    
    leafs = [] # priority queue of leafs
    heapq.heappush(leafs, Leaf(0, root)) 

    while leafs: # while not empty
        leaf = heapq.heappop(leafs)
        for goal in goals:
            if(goal.met(leaf.node.state)):
                return leaf
        for action in actions:
            if(action.available(leaf.node.state)):
                node = Node(addDict(leaf.node.state,action.expectation), leaf.node, action)
                heapq.heappush(leafs, Leaf(leaf.cost+action.cost, node))
    return Leaf(0, root)

# simple wrapper around pathfind to make it easier to use
def plan(goals, actions, startstate):
    print 'starting'
    leaf = pathfind(goals, actions, state)
    print 'done'
    node = leaf.node
    path = []
    while node != None:
        if(node.action != None):
            path.append(node.action)
        node = node.prev
    return reversed(path)

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
        Action(craftTable, {'planks':4}, {'tables':1, 'planks':-4}),
        Action(craftPlank, {'logs':1},   {'planks':4, 'logs':-1}),
        Action(chopWood,   {},           {'logs':1}),
        Action(craftHoe,   {'tables':1, 'planks':2, 'sticks':2}, {'hoes':1,'planks':-2,'sticks':-2}),
        Action(craftSticks,{'planks':2}, {'sticks':4, 'planks':-1}),
        ])
    state = {}
    path = plan(goals, actions, state)
    for action in path:
        action.action(None)

