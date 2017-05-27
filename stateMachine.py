

class StateMachine:
    """A simple state machine"""

    def __init__(self):
        self.states = {} #:dict[string] -> [(check, event, next)]
        self.currentState #:string

    def addState(self, name, transitions):
        """Add a state to the machine"""
        """transitions is a list of condition check, on transition event and next state name triples"""
        self.states[name] = transitions #:[(check, event, next)]

    def update(self):
        """Update the state machine"""
        transitions = self.states[self.currentState]
        for (check, event, nextState) in transitions:
            if check():
                self.currentState = nextState
                event()

