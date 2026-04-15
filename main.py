from mock import Input, System
from scheduler.scheduler import Scheduler

input = Input()
sys = System(input)

scheduler =  Scheduler(input, sys)
scheduler.run()





