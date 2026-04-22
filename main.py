from output import Output
from scheduler.scheduler import Scheduler
from system.system import System
from input import Input
import argparse


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, default="input.txt")
    parser.add_argument("--gui", action="store_true")

    args = parser.parse_args()

    output = Output()
    input = Input(args.input)
    system = System(input, output)

    scheduler = Scheduler(input, system, output)
    try:
        if not args.gui:
            scheduler.run()
        else:
            # Function to start the gui that calls scheduler.run() and reads from the log file
            pass
    except:
        pass 
    finally:
        output.close()
