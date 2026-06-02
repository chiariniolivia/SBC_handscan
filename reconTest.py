


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

    return setsToReturn, recoToReturn

# format is (original cam coordinate, reprojected cam coordinate, cam number)
originalNewSets = []
reconCoords = []
for pair in finderRecoPairs:
    setToAdd, recoToAdd = grabCoords(pair[0],pair[1])
    originalNewSets.append(setToAdd)
    reconCoords.append(recoToAdd)

# 2d to 3d to 2d plot



# 3d visualizer
## this is copied from other code i found because im not reinventing the wheel here
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

# bounds
xMin, xMax = -5, 5
yMin, yMax = -5, 5
zMin, zMax = -8, 1   # interpreted as -8..1

zOffset = 14.71997 - 15.358


plottedCoords = []  # local list of (x,y,z) tuples actually plotted

def inBounds(xArr, yArr, zArr):
    return (xArr >= xMin) & (xArr <= xMax) & (yArr >= yMin) & (yArr <= yMax) & (zArr >= zMin) & (zArr <= zMax)

def collectCoords(xArr, yArr, zArr):
    for xi, yi, zi in zip(xArr, yArr, zArr):
        plottedCoords.append((float(xi), float(yi), float(zi)))

fig = plt.figure(figsize=(10,8))
ax = fig.add_subplot(111, projection='3d')

# ------- vertical lines (at y=0) -------
xPositions = [4.525, -4.525, 4.725, -4.725]
for x in xPositions:
    xs = np.array([x, x])
    ys = np.array([0.0, 0.0])
    zs = np.array([zMin, zMax])  # use full z bounds for line
    mask = inBounds(xs, ys, zs)
    if np.any(mask):
        ax.plot(xs[mask], ys[mask], zs[mask], color='r')
        collectCoords(xs[mask], ys[mask], zs[mask])

# ------- arcs in x-z (centered near +/-2.725) at y=0 -------
def plotArc3DClipped(thetaStart, thetaEnd, rCirc, xCenter, zCenter, yOffset=0.0, color='r'):
    theta = np.linspace(thetaStart, thetaEnd, 400)
    x = rCirc * np.cos(theta) + xCenter
    z = rCirc * np.sin(theta) + zCenter
    y = np.full_like(x, yOffset)
    mask = inBounds(x, y, z)
    if np.any(mask):
        ax.plot(x[mask], y[mask], z[mask], color=color)
        collectCoords(x[mask], y[mask], z[mask])

plotArc3DClipped(0, 1.19367, 2.0,  2.725, zOffset)
plotArc3DClipped(0, 1.19367, 1.8,  2.725, zOffset)
plotArc3DClipped(np.pi - 1.19367, np.pi, 2.0, -2.725, zOffset)
plotArc3DClipped(np.pi - 1.19367, np.pi, 1.8, -2.725, zOffset)

# large central arc (shifted in z by 7.84)
plotArc3DClipped(1.19367, np.pi - 1.19367, 9.4, 0.0, 7.84 + zOffset)
plotArc3DClipped(1.19367, np.pi - 1.19367, 9.2, 0.0, 7.84 + zOffset)

# ------- x-y circles at a chosen z plane -------
theta = np.linspace(0, 2*np.pi, 400)
zPlane = 0.0

x1 = 4.525 * np.cos(theta)
y1 = 4.525 * np.sin(theta)
zArr1 = np.full_like(theta, zPlane)
mask1 = inBounds(x1, y1, zArr1)
if np.any(mask1):
    ax.plot(x1[mask1], y1[mask1], zArr1[mask1], c='r')
    collectCoords(x1[mask1], y1[mask1], zArr1[mask1])

x2 = (4.525 + 0.2) * np.cos(theta)
y2 = (4.525 + 0.2) * np.sin(theta)
zArr2 = np.full_like(theta, zPlane)
mask2 = inBounds(x2, y2, zArr2)
if np.any(mask2):
    ax.plot(x2[mask2], y2[mask2], zArr2[mask2], c='r')
    collectCoords(x2[mask2], y2[mask2], zArr2[mask2])

# ------- r^2 vs z curves mapped into 3D -------
thetaSmall = np.linspace(0, 1.19367, 400)
for rCirc in (2.0, 1.8):
    xCirc = (rCirc * np.cos(thetaSmall) + 2.725)**2
    yHelper = rCirc * np.cos(thetaSmall) + 2.725
    zVals = rCirc * np.sin(thetaSmall) + zOffset
    mask = inBounds(xCirc, yHelper, zVals)
    if np.any(mask):
        ax.plot(xCirc[mask], yHelper[mask], zVals[mask], c='r')
        collectCoords(xCirc[mask], yHelper[mask], zVals[mask])


# add recon coords (this is very complicated!!)
# requires: pip install shapely
from shapely.geometry import Point, Polygon
import numpy as np

# build 2D polygons in x-z plane from sampled red arc curves
nSamples = 800

# sampled outer boundary (large central arc) — note these arcs are in x-z
thetaOuter = np.linspace(1.19367, np.pi - 1.19367, nSamples)
outerX = 9.4 * np.cos(thetaOuter)
outerZ = 9.4 * np.sin(thetaOuter) + (7.84 + zOffset)
outerPts = list(zip(outerX, outerZ))

# sample inner small arcs and inner hole edges clockwise so they are holes
# right small arc (positive x)
thetaRight = np.linspace(0, 1.19367, nSamples)
rightOuterX = 2.0 * np.cos(thetaRight) + 2.725
rightOuterZ = 2.0 * np.sin(thetaRight) + zOffset
rightInnerX = (2.0 - 0.2) * np.cos(thetaRight[::-1]) + 2.725  # reverse for consistent winding
rightInnerZ = (2.0 - 0.2) * np.sin(thetaRight[::-1]) + zOffset

# left small arc (negative x)
thetaLeft = np.linspace(np.pi - 1.19367, np.pi, nSamples)
leftOuterX = 2.0 * np.cos(thetaLeft) - 2.725
leftOuterZ = 2.0 * np.sin(thetaLeft) + zOffset
leftInnerX = (2.0 - 0.2) * np.cos(thetaLeft[::-1]) - 2.725
leftInnerZ = (2.0 - 0.2) * np.sin(thetaLeft[::-1]) + zOffset

# Assemble outer polygon ring: follow outer large arc left->right then small arcs appropriately to form closed loop.
# A reliable approach: combine arcs into a single outer boundary that encloses the volume.
outerRing = []
outerRing.extend(outerPts.tolist())
# connect to right outer small arc end to include its contour
outerRing.extend(list(zip(rightOuterX, rightOuterZ)))
# connect across small gap by adding the inner right arc reversed, then left outer, etc., to form a single closed ring.
# For robustness and clarity, instead build polygon with holes: use large outer ring and small-arc rings as holes.

outerPolygon = Polygon(outerPts)  # large enclosing polygon
holeRight = list(zip(rightOuterX, rightOuterZ)) + list(zip(rightInnerX, rightInnerZ))
holeLeft  = list(zip(leftOuterX, leftOuterZ)) + list(zip(leftInnerX, leftInnerZ))

# create polygonWithHoles
polyWithHoles = Polygon(shell=outerPts, holes=[holeRight, holeLeft])

# classify reconCoords points: project (x,y,z) -> (x,z) and test point-in-polygon
container = reconCoords[0] if len(reconCoords) == 1 and isinstance(reconCoords[0], (list, tuple)) else reconCoords
insideVolume = []
outsideVolume = []

for item in container:
    try:
        coord = item[0]
        x, y, z = float(coord[0]), float(coord[1]), float(coord[2])
    except Exception:
        continue
    if np.isnan(x) or np.isnan(y) or np.isnan(z):
        continue
    # only show points within scene bounds
    if not (xMin <= x <= xMax and yMin <= y <= yMax and zMin <= z <= zMax):
        continue
    pt2 = Point(x, z)
    if polyWithHoles.contains(pt2):
        insideVolume.append((x, y, z))
    else:
        outsideVolume.append((x, y, z))

# plot classified points
if insideVolume:
    rcIn = np.array(insideVolume)
    ax.scatter(rcIn[:,0], rcIn[:,1], rcIn[:,2], c='r', s=20, label='inside red volume')
if outsideVolume:
    rcOut = np.array(outsideVolume)
    ax.scatter(rcOut[:,0], rcOut[:,1], rcOut[:,2], c='b', s=8, label='outside red volume')
ax.legend()


# ------- labels, limits, view -------
ax.set_xlabel('x')
ax.set_ylabel('y')
ax.set_zlabel('z')
ax.set_title('Combined 3D visualization (bounded)')

ax.set_xlim(xMin, xMax)
ax.set_ylim(yMin, yMax)
ax.set_zlim(zMin, zMax)

ax.grid(True)
plt.tight_layout()
plt.show()

