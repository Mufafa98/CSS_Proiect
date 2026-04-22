from scheduler.scheduler import Scheduler
from system.system import System
from input import Input

input = Input("input.txt")
sys = System(input)

scheduler =  Scheduler(input, sys)
scheduler.run()





