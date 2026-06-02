


import sys, os
import matplotlib.pyplot as plt
import numpy as np
from sbcbinaryformat import Streamer, Writer



# grab files
if len(sys.argv) != 3:
    print("Usage: reconTest.py <path to reco version> <path to output> ", file=sys.stderr)        
    sys.exit(2)
root = sys.argv[2]
if not os.path.exists(root):
    print(f"Path does not exist: {root}", file=sys.stderr)
    sys.exit(2)

finderRecoPairs = []
for dirpath, dirnames, filenames in os.walk(root):
    if "reco.sbc" in filenames and "bubble.sbc" in filenames:
        recoPath = os.path.join(dirpath, "reco.sbc")
        bubblePath = os.path.join(dirpath, "bubble.sbc")
        recoData = Streamer(recoPath)
        recoData = recoData.to_dict()
        bubbleData = Streamer(bubblePath)
        bubbleData = bubbleData.to_dict()
        if recoData is None or bubbleData is None:
            continue
        finderRecoPairs.append((bubbleData,recoData))

# grab reco.py 
import importlib.util
def loadModule(path, moduleName):
    path = os.path.expanduser(path)
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    spec = importlib.util.spec_from_file_location(moduleName, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# 2d to 3d to 2d math

def backTo2d(P,x):
    X_h = np.append(x,1.0)
    proj = P @ X_h
    proj = proj[:2] / proj[2]
    return proj


projMatricies = []
P1 = np.array([[-1.05302109e+02, -7.02444185e+02, -3.34577970e+02,  5.72535995e+03], [-5.51213766e+02,  2.58404210e+01, -3.45420423e+02,  3.46877200e+03], [ 5.46200003e-02, -3.31725499e-01, -9.41793422e-01,  8.93247437e+00]])
P2 = np.array([[ 6.24551374e+02,  2.05426176e+02, -4.20327029e+02,  6.08648299e+03],[ 2.38142395e+02, -5.16479247e+02, -3.98154885e+02,  3.57897785e+03], [ 1.75014306e-01,  8.21425255e-02, -9.81133323e-01,  8.45879059e+00]])
P3 = np.array([[-4.46470566e+02,  4.77173422e+02, -4.42541834e+02,  5.80637791e+03], [ 3.67166284e+02,  4.75216795e+02, -4.43358757e+02,  3.38952193e+03], [-9.35610736e-02,  1.48157021e-01, -9.84528223e-01,  7.62754209e+00]])
projMatricies.append(P1)
projMatricies.append(P2)
projMatricies.append(P3)

def grabCoords(bubbleInfo,reconInfo):
    eventsToCheck = []
    for evNum in bubbleInfo["ev"]:
        if evNum in reconInfo["ev"] and not evNum in eventsToCheck:
            eventsToCheck.append(evNum)
    setsToReturn = []
    for evNum in eventsToCheck:
        # find first frame with 2 cameras defined. if three, use all 3.
        cams = []
        fMin = 999
        nMin = 999
        for n in range(0,len(bubbleInfo["frame"])):
                if (bubbleInfo["frame"][n] <= fMin) and (int(bubbleInfo["ev"][n]) == int(evNum)):
                    # check if one or more elements in the list has the same frame and ev value but different cam value, if so set the minimum frame to that frame
                    camsForFrame = []
                    for m in range(len(bubbleInfo["frame"])):
                        if bubbleInfo["ev"][m] == evNum and bubbleInfo["frame"][m] == bubbleInfo["frame"][n]:
                            camVal = bubbleInfo["cam"][m]
                            if not camVal in camsForFrame:
                                camsForFrame.append(camVal)
                    if len(camsForFrame) >= 2:
                        cams = camsForFrame
                        fMin = bubbleInfo["frame"][n]
                        nMin = n 
                        break
        
        recoCord = (-1,-1,-1)
        for i in range(0,len(reconInfo["ev"])):
            if reconInfo["ev"][i] == evNum:
                recoCord = reconInfo["coords_3D"][i]
        if np.isnan(recoCord).any() or len(cams) == 0:
            continue
        for cam in cams:
            original = (np.nan,np.nan)
            for n in range(0,len(bubbleInfo["frame"])):
                if (bubbleInfo["frame"][n] <= fMin) and (int(bubbleInfo["ev"][n]) == int(evNum)) and bubbleInfo["cam"][n] == cam:
                    original= bubbleInfo["pos"][n]
            if np.isnan(original).any():
                continue
            reproj=backTo2d(projMatricies[cam-1],recoCord)
        
            setsToReturn.append((original,reproj,cam))

    return setsToReturn


# format is (original cam coordinate, reprojected cam coordinate, cam number)
originalNewSets = []
for pair in finderRecoPairs:
    originalNewSets.append(grabCoords(pair[0],pair[1]))


# 2d to 3d to 2d plot



# 3d visualizer










