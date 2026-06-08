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

def plot_camera_subplot(ax, items, cam_id):
    if not items:
        ax.axis('off')
        ax.set_title(f'Camera {cam_id}\n(no data)')
        return
    orig = np.array([it[0] for it in items])
    new  = np.array([it[1] for it in items])
    deltas = new - orig
    dists = np.linalg.norm(deltas, axis=1)
    ax.set_aspect('equal', adjustable='box')
    ax.grid(True, linestyle='--', alpha=0.4)
    ax.scatter(orig[:,0], orig[:,1], c='blue', zorder=3)
    ax.scatter(new[:,0],  new[:,1],  c='red',  zorder=3)
    max_dist = max(1.0, dists.max())
    for i, (x0, y0) in enumerate(orig):
        dx, dy = deltas[i]
        ax.arrow(x0, y0, dx, dy,
                 length_includes_head=True,
                 head_width=0.06 * max_dist,
                 head_length=0.09 * max_dist,
                 fc='gray', ec='gray', alpha=0.8)
    ax.set_title(f'Camera {cam_id}')
    ax.set_xlabel('')
    ax.set_ylabel('')
    ax.invert_yaxis()  # y=0 at top, increasing downward visually

groups = {1: [], 2: [], 3: []} 
for item in originalNewSets:
    cam = int(item[2])
    if cam in groups:
        groups[cam].append(item)
fig, axes = plt.subplots(1, 3, figsize=(15, 5))
for i, cam_id in enumerate((1, 2, 3)):
    plot_camera_subplot(axes[i], groups[cam_id], cam_id)
plt.tight_layout()
plt.show()


## 2d to 3d to 2d histogram
dists_by_cam = {1: [], 2: [], 3: []}
for old, new, cam in originalNewSets:
    old = np.asarray(old, dtype=float)
    new = np.asarray(new, dtype=float)
    dist = np.linalg.norm(new - old)
    dists_by_cam[int(cam)].append(dist)
all_dists = np.concatenate([np.asarray(dists_by_cam[k]) for k in (1, 2, 3)]) if any(dists_by_cam.values()) else np.array([])
if all_dists.size:    
    bins = np.linspace(0, all_dists.max(), 30)
else:
    bins = 30
colors = {1: 'tab:blue', 2: 'tab:orange', 3: 'tab:green'}
alpha = 0.5
plt.figure(figsize=(8, 5))
for cam in (1, 2, 3):
    plt.hist(dists_by_cam[cam], bins=bins, color=colors[cam], alpha=alpha,
             label=f'cam {cam}', edgecolor='black', linewidth=0.3)
plt.xlabel('Distance between coordinates (pixels)')
plt.ylabel('Count')
plt.title('Reprojection error')
plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()
plt.show()


# 3d visualizer
# modified from event viewer, https://github.com/SBC-Collaboration/LAr10Ana/blob/main/EventDisplay/eventdisplay/tabs/three_d_bubble.py
# z vs x (or y)
plt.vlines(4.525,-8.75,14.71997 - 15.358,color='r')
plt.vlines(-4.525,-8.75,14.71997 - 15.358,color='r')
plt.vlines(4.725,-8.75,14.71997 - 15.358,color='r')
plt.vlines(-4.725,-8.75,14.71997 - 15.358,color='r')

theta = np.linspace(0, 1.19367, 400)
rcirc = 2
xcirc = rcirc * np.cos(theta) + 2.725
ycirc = rcirc * np.sin(theta) + 14.71997 - 15.358
plt.plot(xcirc, ycirc, c='r')
theta = np.linspace(0, 1.19367, 400)
rcirc = 2 - 0.2
xcirc = rcirc * np.cos(theta) + 2.725
ycirc = rcirc * np.sin(theta) + 14.71997 - 15.358
plt.plot(xcirc, ycirc, c='r')
theta = np.linspace(np.pi - 1.19367, np.pi, 400)
rcirc = 2
xcirc = rcirc * np.cos(theta) - 2.725
ycirc = rcirc * np.sin(theta) + 14.71997 - 15.358
plt.plot(xcirc, ycirc, c='r')
theta = np.linspace(np.pi - 1.19367, np.pi, 400)
rcirc = 2 - 0.2
xcirc = rcirc * np.cos(theta) - 2.725
ycirc = rcirc * np.sin(theta) + 14.71997 - 15.358
plt.plot(xcirc, ycirc, c='r')
theta = np.linspace(1.19367, np.pi-1.19367, 400)
rcirc = 9.4
xcirc = rcirc * np.cos(theta)
ycirc = rcirc * np.sin(theta) + 7.84 - 15.358
plt.plot(xcirc, ycirc, c='r')
theta = np.linspace(1.19367, np.pi-1.19367, 400)
rcirc = 9.4 - 0.2
xcirc = rcirc * np.cos(theta)
ycirc = rcirc * np.sin(theta) + 7.84 - 15.358
plt.plot(xcirc, ycirc,c='r')

for coord in reconCoords:
    plt.scatter( coord[0][0], coord[0][2])


plt.xlabel("x")
plt.ylabel("z")
plt.title("z vs x")
plt.grid(True)
plt.legend()
plt.show()




# y vs x

theta = np.linspace(0, 2*np.pi, 400)
plt.plot(4.525*np.cos(theta), 4.525*np.sin(theta), c='r')
plt.plot((4.525+0.2)*np.cos(theta), (4.525+0.2)*np.sin(theta), c='r')
for coord in reconCoords:
    plt.scatter( coord[0][0], coord[0][1])


plt.xlabel("x")
plt.ylabel("y")
plt.title("y vs x")
plt.xlim(-5,5)
plt.ylim(-5,5)
plt.grid(True)
plt.legend()
plt.show()




# r2 vs z

plt.vlines(4.525**2,-8.75,14.71997 - 15.358,color='r')
plt.vlines(4.725**2,ymin=-8.75,ymax=14.71997 - 15.358,color='r')

theta = np.linspace(0, 1.19367, 400)
rcirc = 2
plt.plot((rcirc*np.cos(theta)+2.725)**2,
         rcirc*np.sin(theta)+14.71997-15.358,c='r')

rcirc = 1.8
plt.plot((rcirc*np.cos(theta)+2.725)**2,
         rcirc*np.sin(theta)+14.71997-15.358,c='r')

for coord in reconCoords:
    plt.scatter( (coord[0][0]**2 + coord[0][1]**2), coord[0][2])



plt.xlabel("r2")
plt.ylabel("z")
plt.title("r2 vs z")
plt.grid(True)
plt.legend()
plt.show()
