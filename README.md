## Run Task Input-Output Flow

From the repository root:

```bash
python main.py --gui
```

Input is read from:

- ./input.txt

Outputs are generated automatically:
- logs/log.txt

The script also prints the same information in the terminal.

## Input Format (./input.txt)

Example:

```text
PROCESSORS 3
MEMORY 160
TIMESLICE 3
SYS_PERIOD 15
DISK_RATE 8

PROCESS 0 48 0 6 2 4 1 5
PROCESS 1 64 0 3 4 7
```
