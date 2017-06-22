

class StateMachine:
	"""A simple state machine"""

	def __init__(self):
		self.__states = {} #:dict[string] -> [(check, event, next)]
		self.actions = {} #:dict[string] -> action
		self.currentState = "start" #:string
		self.addState("start")

	def addState(self, name):
		"""register a state name"""
		if name not in self.__states:
			self.__states[name] = []

	def addTransition(self, fromState, toState, condition, event):
		transition = (condition, event, toState)
		self.__states[fromState].append(transition)

	def update(self):
		"""Update the state machine"""
		transitions = self.__states[self.currentState]

		for (check, event, nextState) in transitions:
			if check():
				self.currentState = nextState
				print "sm new state: ", nextState
				event()

		action =  self.actions.get(self.currentState)

		if action is not None:
			action()
