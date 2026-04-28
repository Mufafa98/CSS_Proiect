from output import Output
from scheduler.scheduler import Scheduler
from system.system import System
from input import Input
import argparse
import threading
from pathlib import Path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, default="input.txt")
    parser.add_argument("--gui", action="store_true")

    args = parser.parse_args()

    if args.gui:
        log_path = Path("./logs/log.txt")
        try:
            log_path.unlink()
        except FileNotFoundError:
            pass

    output = Output()
    input = Input(args.input)
    system = System(input, output)

    scheduler = Scheduler(input, system, output)
    scheduler_thread = None
    try:
        if not args.gui:
            scheduler.run()
        else:
            scheduler_thread = threading.Thread(target=scheduler.run, daemon=False)

            def _start_scheduler() -> None:
                if scheduler_thread is not None and scheduler_thread.ident is None:
                    scheduler_thread.start()

            from ui.ui import ui as start_ui

            start_ui(on_started=_start_scheduler)
    except Exception as ex:
        print(f"exception: {ex}")
    finally:
        if scheduler_thread is not None and scheduler_thread.ident is not None:
            scheduler_thread.join()
        output.close()
