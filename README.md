# SBC_handscan
A script for handscaning SBC events. To be ran from LAr10Ana setup.sh conda enviorment. At the moment, this is to be used in conjunction with the event viewer. You find the event you want in event viewer, note the first frame of bubble formation, then run this script with that frame as -i, and write down the coordinates.

## Usage:
```bash
python handscan.py -e EVENT [-s SCRATCH_DIR] [-l LOGGING] [-i INDEX]
```
Event is the event title as found in SBC-25-daqdata, the scratch dir is for temporary untaring of the event, -l is a logging flag, -i is the bubble formation index.

## Dependencies
TODO



