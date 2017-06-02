from goapy import Planner, Action_List

def chopWood(arg):
    print 'chopping wood! chop chop...'

def craftTable(arg):
    print 'crafting crafting table! table... in the color %s' % arg

def craftPlank(arg):
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

    world.set_action_list(actions)

    t = time.time()
    path = world.calculate()
    took_time = time.time() - t

    for p in path:
        actions.do_the_thing(p['name'], 'red')
        print path.index(p)+1, p['name']

    print '\nTook:', took_time

