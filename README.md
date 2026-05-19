# SBC Handscan Helper
A script for grabbing informtaion on SBC events. To be ran within the LAr10Ana setup.sh conda environment. At the moment, this is to be used in conjunction with the event viewer.
Questions?

`oac38 at drexel.edu`
## Usage:
```bash
 handscan.py [-h] [-l] [-E] -r RUN [-e EVENT]  [-o OUTPUT.csv]
```
### Parameters:
RUN is the run title as found in SBC-25-daqdata.

EVENT is the event number within the given run. Assumed 0 if not given.

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



