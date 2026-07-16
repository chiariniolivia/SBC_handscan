# this is just so slow and also the geometry is wrong it isnt worth looking at
# 3d visualizer
# modified from event viewer, https://github.com/SBC-Collaboration/LAr10Ana/blob/main/EventDisplay/eventdisplay/tabs/three_d_bubble.py
from sbcbinaryformat import Streamer, Writer
import sys, os
import numpy as np
from math import cos, sin
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
# grab files
if len(sys.argv) != 3:
    print("Usage: reconTest.py <path to reco version> <path to output> ", file=sys.stderr)        
    sys.exit(2)
recover = sys.argv[1]
root = sys.argv[2]
if not os.path.exists(root):
    print(f"Path does not exist: {root}", file=sys.stderr)
    sys.exit(2)

limiter = 150
count = 0
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
        print(recoData)
        finderRecoPairs.append((bubbleData,recoData))
        count += 1
    if count >= limiter:
        break
# grab reco.py 
import importlib.util
def loadModule(path, moduleName):
    path = os.path.expanduser(path)
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    spec = importlib.util.spec_from_file_location(moduleName, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    func = getattr(module,moduleName)
    return func
getProjMat = loadModule(recover, "getProjMat")

# 2d to 3d to 2d math

def backTo2d(P,x):
    x = x /25.4
    X_h = np.append(x,1.0)
    proj = P @ X_h
    proj = proj[:2] /proj[2] 
    return proj 


projMatricies = []
projMatricies.append(getProjMat(1))
projMatricies.append(getProjMat(2))
projMatricies.append(getProjMat(3))
def grabCoords(bubbleInfo,reconInfo):
    eventsToCheck = []
    for evNum in bubbleInfo["ev"]:
        if evNum in reconInfo["ev"] and not evNum in eventsToCheck:
            eventsToCheck.append(evNum)
    setsToReturn = []
    newFrames = [f for row in reconInfo["frame"] for f in row]
    
    recoToReturn = []
    for evNum in eventsToCheck:
        for f  in range(50):
            # reco should tell us if the frame is good or not    
            curReco = None
            done = False
            for i in range(0,len(reconInfo["ev"])):
                if reconInfo["ev"][i] == evNum:
                    for j in range(len(reconInfo["frame"][i])):
                        if reconInfo["frame"][i][j] == f and i+j <len(reconInfo["coords_3D"]):
                            recoCord = reconInfo["coords_3D"][i+j]
                            if not (np.isnan(recoCord).any() or recoCord[0] <= -999):
                                curReco = (recoCord)
                                done = True
                                break
                if done:
                    break
            # if there wasnt a good value, we can just move to the next frame
            if curReco is None or np.isnan(curReco).any():
                continue
            
            # list of cameras that have bubbles in this frame
            camsForFrame = []
            # list of indicies of enteries for bubbles in this frame
            iList = []
            # list of bubble finder coordinate- camera pairs
            oList = []
            for n in range(len(bubbleInfo["frame"])):
                if (int(bubbleInfo["ev"][n]) == int(evNum)) and (int(bubbleInfo["frame"][n] == f)):
                    for m in range(len(bubbleInfo["frame"])):
                        if (int(bubbleInfo["ev"][m]) == int(evNum)) and (int(bubbleInfo["frame"][m]) == int(bubbleInfo["frame"][n])):
                            camVal = bubbleInfo["cam"][m]
                            checkList = {t[0] for t in camsForFrame}
                            if (not camVal in checkList) and (m not in iList) :
                                camsForFrame.append((camVal,evNum))
                                iList.append(m)
            # if not more than one cam, who cares move on.
            if len(camsForFrame) < 2:
                continue
            for i in iList:
                oList.append((bubbleInfo["pos"][i], bubbleInfo["cam"][i], bubbleInfo["ev"][i]))

            for o in oList:
                setsToReturn.append((o[0], backTo2d(projMatricies[o[1]-1],curReco), o[1], o[2]))
            recoToReturn.append((curReco, evNum))
    return setsToReturn, recoToReturn

# format is (original cam coordinate, reprojected cam coordinate, cam number)
originalNewSets = []
reconCoords = []
for pair in finderRecoPairs:
    
    setsToAdd, recosToAdd = grabCoords(pair[0],pair[1])
    evSet = []
    recoSet = []
    for setToAdd in setsToAdd:
        evSet.append(setToAdd)
    for recoToAdd in recosToAdd:
        recoSet.append(recoToAdd)
    originalNewSets.append(evSet)
    reconCoords.append(recoSet)

def plot_cylinder_bowl(radius, positive_z, negative_z, ax=None, wire_alpha=0.2, base_f=50):
    
    r = float(radius)
    pz = float(positive_z)
    nz = float(negative_z)
    # Create axes if not provided
    fig = None    
    if ax is None:
        fig = plt.figure(figsize=(8, 6))
        ax = fig.add_subplot(111, projection='3d')
    # Upper cylinder (polar coords)
    u = np.linspace(0, 2 * np.pi, 100)
    
    z_samples = max(2, int(max(1.0, abs(pz)) / 2)) if pz != 0 else 2
    z = np.linspace(0, abs(pz), z_samples)
    U, Z = np.meshgrid(u, z)
    rstride = 1 + int((abs(pz) + abs(nz)) / 2 / 20)
    cstride = 5
    ax.plot_wireframe(r * np.cos(U), r * np.sin(U), np.sign(nz) * -Z,
                      alpha=wire_alpha, rstride=rstride, cstride=cstride)
    
    u = np.linspace(0, 2 * np.pi, 100)
    v_samples = max(2, int(max(1.0, abs(nz)) / 2)) if nz != 0 else 2
    v = np.linspace(np.pi / 2, np.pi, v_samples)
    U, V = np.meshgrid(u, v)
    rstride = 1 + int((abs(pz) + abs(nz)) / 2 / 40)
    cstride = 5
    ax.plot_wireframe(r * np.cos(U) * np.sin(V),
                      r * np.sin(U) * np.sin(V),
                      -nz * np.cos(V),
                      alpha=wire_alpha, rstride=rstride, cstride=cstride)
    
    f = float(base_f)
    ax.set_xlim(-r - f, r + f)
    ax.set_ylim(-r - f, r + f)
    if np.sign(nz) == 1:
        ax.set_zlim(-pz + f, nz - f)
    else:
        ax.set_zlim(nz - f, -pz + f)
    
    ax.set_xlabel('X (mm)')
    ax.set_ylabel('Y (mm)')
    ax.set_zlabel('Z (mm)')
    return fig, ax


fig, ax = plot_cylinder_bowl(radius=200,
                             positive_z=600,
                             negative_z=100)
for coordSet in reconCoords:
    for coord in coordSet:
        x,y,z = coord[0]
        # 25.4 is to convert from inches to mm
        ax.scatter(x*25.4,y*25.4,z*25.4)

plt.show()
