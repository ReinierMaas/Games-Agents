from goapy import Planner, Action_List

def chopWood(w):
    print 'chopping wood! chop chop...'

def craftTable(w):
    print 'crafting crafting table! table...'

def craftPlank(w):
    print 'crafting planks! plank plank...'

if __name__ == '__main__':
    import time
    world = Planner('planks', 'crafting_tables', 'logs')
    world.set_start_state(planks=0, crafting_tables=0, logs=0)
    world.set_goal_state(crafting_tables=1)

    actions = Action_List()

    actions.add_action('craft_table',  craftTable, {'planks':4}, {'crafting_tables':1, 'planks':-4})
    actions.add_action('craft_planks', craftPlank, {'logs':1},   {'planks':4, 'logs':-1})
    actions.add_action('chop_wood',    chopWood,   {},           {'logs':1})

    world.set_action_list(actions)

    t = time.time()
    path = world.calculate()
    took_time = time.time() - t

    for p in path:
        actions.do_the_thing(p['name'], 'red')
        print path.index(p)+1, p['name']

    print '\nTook:', took_time

# future idea to make defining actions more flexible by using functions
# may be overkill, but would definitly be cool
class CraftTable:
    def priority(w):
        return 1
    def requires(w): 
        return w['planks']>=4
    def changes(w):
        return {'crafting_tables':1,'planks':-4}
    def does(arg):
        print 'crafting tables!'

