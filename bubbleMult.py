from sbcbinaryformat import Streamer, Writer
from collections import Counter, defaultdict
import numpy as np


def bubble_mult(bubble_data, ev):
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
    n = 5
    seq = [(f, c, s) for f, c, s, e  in zip(frames, cams, events, sigs) if ( f >= firstFrame and f <= firstFrame + (10 + n) and e == int(ev))]
    if not seq:
        return 0

    mult = Counter(seq)  # {(frame, cam, significance): multiplicity}
    byCamDict = defaultdict(dict)
    lastSeen = set()
    for f, c, s  in seq:
        if (f,c) not in lastSeen:
            byCamDict[c][f] = mult[(f,c)]
            lastSeen.add((f,c)) 
   
    
    sortedByMult = sorted(mult.keys(), key = lambda k: mult[k], reverse=True)
    checked  = []
    for f0, c0, s0 in sortedByMult:
        if ( (f0,c0) in checked) or s0 <= 0.75:
            print(s0)
            continue
        checked.append((f0,c0))
        m0 = mult[(f0,c0)]
        ok = True
        for offset in range(n):    
            if  mult[f0 + offset, c0] < mult[f0, c0]:
                ok = False
                break
        if ok:
            return m0
    return 0


reconPath = '/exp/e961/data/SBC-25-recon/dev-output/' 

runsToCheck = [("20260212_0",3), ("20260212_1",5)]
for run, ev in runsToCheck:
    bubbleData = Streamer(reconPath + run + '/bubble.sbc').to_dict()
    print(bubble_mult(bubbleData,ev))


