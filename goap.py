from goapy import Planner, Action_List

def update():
    pass

def perform_action():
    pass

def chopWood():
    print 'chopping wood! chop chop...'

def craftTable():
    print 'crafting crafting table! table...'

def craftPlank():
    print 'crafting planks! plank plank...'


if __name__ == '__main__':
    import time
    world = Planner('has_4_planks', 'has_crafting_table', 'has_logs')
    world.set_start_state(has_4_planks=False, has_logs=False, has_crafting_table=False)
    world.set_goal_state(has_crafting_table=True)

    actions = Action_List()

    actions.add_action('craft_table', craftTable, {'has_4_planks':True}, {'has_crafting_table':True})
    actions.add_action('craft_planks', craftPlank, {'has_logs':True}, {'has_4_planks':True})
    actions.add_action('chop_wood', chopWood, {}, {'has_logs':True})

    #actions.add_condition('craft_table', has_4_planks=True)
    #actions.add_reaction('craft_table', has_crafting_table=True, has_4_planks=False)
    #actions.set_weight('craft_table', 1)

    #actions.add_condition('craft_planks', has_logs=True)
    #actions.add_reaction('craft_planks', has_4_planks=True, has_logs=False)
    #actions.set_weight('craft_planks', 1)

    #actions.add_condition('chop_wood')
    #actions.add_reaction('chop_wood', has_logs=True)
    #actions.set_weight('chop_wood', 1)

    world.set_action_list(actions)

    t = time.time()
    path = world.calculate()
    took_time = time.time() - t

    for p in path:
        print path.index(p)+1, p['name']

    print '\nTook:', took_time

