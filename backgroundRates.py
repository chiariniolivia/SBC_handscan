import matplotlib.pyplot as plt
import numpy as np
import sys, csv, glob, os
from sbcbinaryformat import Streamer, Writer

## warm annular
backgroundRunsWarm = []
## cold annular
backgroundRunsCold = []

## 199k
backgroundRunsHot = []


## ones to use for rate calculation
backgroundList = []
for run in backgroundRunsWarm:
    backgroundList.append(run)
for run in backgroundRunsCold:
    backgroundList.append(run)
for run in backgroundRunsHot:
    backgroundList.append(run)



def process_dir_txt(dirpath):
    checkedRuns = []
    returnList = []
    for path in glob.glob(os.path.join(dirpath, "*.txt")):
        with open(path, 'r', encoding='utf-8') as f:
            for raw in f:
                parts = raw.split()
                if len(parts) < 5:
                    continue
                run = parts[0]
                ev = parts[1]
                try:
                    mult = int(parts[4])
                    region =int(parts[3])
                except ValueError:
                    continue
                if run not in backgroundList:
                    checkedRuns.append((ev,run))
                    continue
                if (ev,run) in checkedRuns:
                    continue
                returnList.append((run,ev,mult))
                checkedRuns.append((ev,run))
    return returnList


handScannedBackgrounds = process_dir_txt('/exp/e961/data/SBC-25-handscan/')


def process_dir_ana(dirpath):
    outList = []

    subdirs = {os.path.basename(p.rstrip(os.sep)) for p in glob.glob(os.path.join(dirpath, '*/'))}
    for item in handScannedBackgrounds:
        dirname = item[0]
        if dirname in subdirs:
            fullPath = os.path.join(dirpath, dirname)
            expData = Streamer(fullPath + 'exposure.sbc').to_dict()
            for i in range(len(expData["ev"])):
                if expData["ev"][i] == item[1] and expData['PT2121_livetime'][i] > 1:
                    outList.append((item[2], expData['PT2121_livetime'][i]))

    return outList



backgroundPairs = process_dir_ana('/exp/e961/data/SBC-25-recon/v0.1.2/')

backgroundTime = 0
backgroundSingles = 0
backgroundMultis  = 0
for i in range(len(backgroundPairs)):
    if backgroundPairs[i][0] == 1:
        backgroundSingles += 1
    elif backgroundPairs[i][0] != 0:
        backgroundMultis += 1
    backgroundTime += backgroundPairs[i][1]

#convert to per hour
backgroundTime *= 60*60
print("Background sinlges rate is "+ str(backgroundSingles/backgroundTime) +"/hr")
print("Background multi rate is "+ str(backgroundMultis/backgroundTime) +"/hr")
