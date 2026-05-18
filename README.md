# SBC Handscan Helper
A script for handscaning SBC events. To be ran within the LAr10Ana setup.sh conda environment. At the moment, this is to be used in conjunction with the event viewer. You find the event you want in the event viewer, note the first frame of bubble formation in each camera, then run this script with that frame as -i (for each camera), and write down the coordinates given in the terminal and by using pyplot's image display.
Questions?

`oac38 at drexel.edu`
## Usage:
```bash
 handscan.py [-h] [-l] [-E] -r RUN [-e EVENT]  [-o OUTPUT.csv]
```
### Parameters:
RUN is the run title as found in SBC-25-daqdata.

EVENT is the event number within the given run. Assumed 0 if not given.

INDICES are the 3 guesses at formation frames for each camera. Uses the bubble finder earliest guess if not given.

SCRATCH is the directory for files to be extracted to while running, which is cleared after the script run unless flagged otherwise.
### Flags
-h prints the help message

-l enables logging messages which are printed to stdout

-E enables running for all available events


## Dependencies
All are included in the LAr10Ana conda enviorment.
```python
sys, os, csv, argparse,  shutil, warnings, atexit
collections
numpy
sbcbinaryformat
```



