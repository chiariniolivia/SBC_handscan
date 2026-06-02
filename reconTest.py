


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
    recoToReturn = []
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
                if not np.isnan(recoCord).any() or len(cams) == 0 :
                    recoToReturn.append((recoCord, reconInfo["runid"][i], reconInfo["ev"][i]))
                    break
        if np.isnan(recoCord).any() or len(cams) == 0:
            continue
    
        for cam in cams:
            original = (np.nan,np.nan)
            for n in range(0,len(bubbleInfo["frame"])):
                if (bubbleInfo["frame"][n] <= fMin) and (int(bubbleInfo["ev"][n]) == int(evNum)) and bubbleInfo["cam"][n] == cam:
                    original= bubbleInfo["pos"][n]
                    break
            if np.isnan(original).any():
                continue
            reproj=backTo2d(projMatricies[cam-1],recoCord)
            setsToReturn.append((original,reproj,cam))
    return setsToReturn, recoToReturn

# format is (original cam coordinate, reprojected cam coordinate, cam number)
originalNewSets = []
reconCoords = []
for pair in finderRecoPairs:
    setsToAdd, recosToAdd = grabCoords(pair[0],pair[1])
    for setToAdd in setsToAdd:
        originalNewSets.append(setToAdd)
    for recoToAdd in recosToAdd:
        reconCoords.append(recoToAdd)

# 2d to 3d to 2d plot

# 3d visualizer
# modified from event viewer, https://github.com/SBC-Collaboration/LAr10Ana/blob/main/EventDisplay/eventdisplay/tabs/three_d_bubble.py

from math import cos, sin
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
def plot_cylinder_bowl(radius, positive_z, negative_z, ax=None, wire_alpha=0.2, base_f=50):
    """    Plot an upper cylinder (height = positive_z) and a lower spherical bowl (depth = negative_z).
    radius, positive_z, negative_z: numeric (can be negative for direction; signs are handled).
    ax: optional matplotlib 3D Axes. If None, a new figure and axes are created and returned.
    wire_alpha: alpha for wireframes.
    base_f: padding applied to axis limits (same role as `f` in original).
    Returns: (fig, ax) where fig may be None if an existing ax was passed.
    """
    # Ensure floats
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
    # use at least 2 samples in z-direction
    z_samples = max(2, int(max(1.0, abs(pz)) / 2)) if pz != 0 else 2
    z = np.linspace(0, abs(pz), z_samples)
    U, Z = np.meshgrid(u, z)
    rstride = 1 + int((abs(pz) + abs(nz)) / 2 / 20)
    cstride = 5
    ax.plot_wireframe(r * np.cos(U), r * np.sin(U), np.sign(nz) * -Z,
                      alpha=wire_alpha, rstride=rstride, cstride=cstride)
    # Lower bowl (sphere cap) using polar coords
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
    # Set graph limits with padding
    f = float(base_f)
    ax.set_xlim(-r - f, r + f)
    ax.set_ylim(-r - f, r + f)
    if np.sign(nz) == 1:
        ax.set_zlim(-pz + f, nz - f)
    else:
        ax.set_zlim(nz - f, -pz + f)
    # Label axes
    ax.set_xlabel('X (mm)')
    ax.set_ylabel('Y (mm)')
    ax.set_zlabel('Z (mm)')
    return fig, ax


fig, ax = plot_cylinder_bowl(radius=2*25.4,
                             positive_z=0*25.4,
                             negative_z=-8*25.4)
plt.show()


