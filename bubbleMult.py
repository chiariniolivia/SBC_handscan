from sbcbinaryformat import Streamer, Writer
from collections import Counter, defaultdict
import csv
import numpy as np


def bubble_mult(run, ev):
    reconPath = '/exp/e961/data/SBC-25-recon/v0.2.0/' 
    bubble_data = Streamer(reconPath + run + '/bubble.sbc').to_dict()
    frames  = [int(f) for f in bubble_data["frame"]]
    cams    = [int(c) for c in bubble_data["cam"]]
    events  = [int(e) for e in bubble_data["ev"]]    
    sigs    = [float(s) for s in bubble_data["significance"]]
    # find first mutli cam frame
    firstFrame = -1
    idx = sorted(range(len(frames)), key=lambda i: frames[i])
    seen = set()
    for i in idx:
        seen.add(cams[i])
        if len(seen) >= 2:
            firstFrame = frames[i]
            break

    # get all camera frame pairs within a range of the first mutli cam event
    n = 2
    seq = [(f, c) for f, c, s, e  in zip(frames, cams, sigs, events) if ( f >= firstFrame and f <= firstFrame + (10 + n) and int(e) == int(ev) and float(s) >= 0.75)]
    if not seq:
        return -1
     
    maxFrame = 1
    try:
        with open('/exp/e961/data/SBC-25-unpacked/' + str(run) + '/' + str(ev) + '/cam1.log') as f:
            reader = csv.reader(f)
            header = next(reader)
            for row in reader:
                maxFrame += 1
                if maxFrame >= 50:
                    break
    except:
        with open('/exp/e961/data/SBC-25-unpacked/' + str(run) + '/' + str(ev) + '/cam2.log') as f:
            reader = csv.reader(f)
            header = next(reader)
            for row in reader:
                maxFrame += 1
                if maxFrame >= 50:
                    break

    mult = Counter(seq)  # {(frame, cam): multiplicity}
    byCamDict = defaultdict(dict)
    lastSeen = set()
    for f, c  in seq:
        if (f,c) not in lastSeen:
            byCamDict[c][f] = mult[(f,c)]
            lastSeen.add((f,c)) 
   
    
    sortedByMult = sorted(mult.keys(), key = lambda k: mult[k], reverse=True)
    checked  = []
    
    for f0, c0 in sortedByMult:
        if ( (f0,c0) in checked):
            continue
        checked.append((f0,c0))
        m0 = mult[(f0,c0)]
        ok = True
        for offset in range(n):    
            if f0 + offset >= maxFrame:
                break
            disagree  = (mult[f0 + offset, c0] < m0)
            disagree += (mult[f0 + offset, c0] < m0)
            disagree += (mult[f0 + offset, c0] < m0)
            if disagree >= 2:
                ok = False
                break
        if ok:
            return m0
        
    return -2


runsToCheck = [("20260212_0",0), ("20260212_1",5), ("20260213_4",16)]
for i in range(0,25):
    runsToCheck.append(("20251113_11",i))
for run, ev in runsToCheck:
    print(run+str(ev))
    print(bubble_mult(run,ev))





