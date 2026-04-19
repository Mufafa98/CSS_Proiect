## Run Task Input-Output Flow

From the repository root:

```bash
python "task_input-output/main.py"
```

Input is read from:

- task_input-output/input.txt

Outputs are generated automatically:
- task_input-output/simulation_log.txt
- task_input-output/simulation_stats.txt

The script also prints the same information in the terminal.

## Input Format (task_input-output/input.txt)

Example:

```text
PROCESSORS 3
MEMORY 160
TIMESLICE 3
SYS_PERIOD 15
DISK_RATE 8

PROCESS 0 48 6 2 4 1 5
PROCESS 1 64 3 4 7
```
