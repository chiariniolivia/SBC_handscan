# SBC_handscan
A script for handscaning SBC events. To be ran within the LAr10Ana setup.sh conda enviorment. At the moment, this is to be used in conjunction with the event viewer. You find the event you want in event viewer, note the first frame of bubble formation, then run this script with that frame as -i (for each camera), and write down the coordinates.

## Usage:
```bash
 handscan.py [-h] -r RUN [-e EVENT] [-i INDICES INDICES INDICES] [-R] [-l] [-s SCRATCH] [-k]
```
### Parameters:
RUN is the run title as found in SBC-25-daqdata.
EVENT is the event number within the given run. Assumed 0 if not given.
INDICES are the 3 guesses at formation frames for each camera. Uses the bubble finder earliest guess if not given.
SCRATCH is the directory for files to be extracted to while running, which is cleared after the script run unless flagged otherwise.
### Flags
-h prints the help message
-R stops the program after getting bubble and reconsturction info
-l enables logging messages which are printed to stdout
-k keeps the scratch direcotry between runs, useful if checking multiple events within the same run

## Dependencies
```
sys, os, argparse, tarfile, shutil, warnings
matplotlib
numpy
PIL
sbcbinaryformat
```

