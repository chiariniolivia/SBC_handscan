import sys, os
import matplotlib.pyplot as plt
import numpy as np
from sbcbinaryformat import Streamer, Writer

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

import colorsys
import hashlib
import random
def color_for_index(i):
    SMIN = 0.4
    SMAX = 0.9
    VMIN = 0.7
    VMAX = 1.0
    h = hashlib.md5(str(i).encode()).digest()
    hue = ((h[0] << 8) | h[1]) / 65535.0
    s_raw = ((h[2] <<8) | h[3])/ 65535.0
    v_raw = ((h[4] <<8) | h[5])/ 65535.0
    s = SMIN + s_raw * (SMAX - SMIN)
    v = VMIN + v_raw * (VMAX - VMIN)
    r,g,b =  colorsys.hsv_to_rgb(hue, s, v)
    ran1 = random.Random(i).random()
    ran2 = random.Random(i+100).random()
    ran3 = random.Random(i+101).random()
    return (ran1,ran2,ran3)

def plot_camera_subplot(ax, items, cam_id):
    if not items:
        ax.axis('off')
        ax.set_title(f'Camera {cam_id}\n(no data)')
        return

    orig = np.array([it[0] for it in items])
    new  = np.array([it[1] for it in items])
    indices = [int(it[3]) for it in items]
    colors = np.array([color_for_index(idx) for idx in indices])
    deltas = new - orig
    dists = np.linalg.norm(deltas, axis=1)
    maxDist = 350
    outlierMask = (dists <= maxDist)
    
    ax.set_aspect('equal', adjustable='box')
    ax.grid(True, linestyle='--', alpha=0.4)
    ax.scatter(orig[outlierMask,0], orig[outlierMask,1], c=colors[outlierMask], zorder=3)
    ax.scatter(new[outlierMask,0],  new[outlierMask,1],  c='red',  zorder=3)
    max_dist = max(1.0, dists.max())
    for i in np.nonzero(outlierMask)[0]:
        x0, y0 = orig[i]
        dx, dy = deltas[i]
        ax.arrow(x0, y0, dx, dy,
                 length_includes_head=True,
                 fc='gray', ec='gray', alpha=0.8)
    ax.set_title(f'Camera {cam_id}')
    #ax.set_xlim(-500,900)
    #ax.set_ylim(-500,1400)
    ax.set_xlabel('x (pixels)')
    ax.set_ylabel('y (pixels)')
    ax.invert_yaxis()

if count == 1:
    groups = {1: [], 2: [], 3: []}
    for curSet in originalNewSets:
        for item in curSet:
            cam = int(item[2])
            if cam in groups:
                groups[cam].append((item))

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    for i, cam_id in enumerate((1, 2, 3)): 
       plot_camera_subplot(axes[i], groups[cam_id], cam_id)
    plt.tight_layout()
    plt.savefig("camVisual.png")
    plt.close()

    dists_by_cam = {1: [], 2: [], 3: []}
    wayTooFarAway = 0
    total = 0
    for curSet in originalNewSets:
        for old, new, cam, ev in curSet:
            total += 1
            old = np.asarray(old, dtype=float)
            new = np.asarray(new, dtype=float)

            dist = np.linalg.norm(new - old)
            if dist <= 2000:
                dists_by_cam[int(cam)].append(dist)
                if dist > 150: 
                    wayTooFarAway += 1
            else:
                wayTooFarAway +=1
    print(f"More than 150 pixels away reproj error:\t" + str(wayTooFarAway) + "/" + str(total))
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
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.legend()
    plt.savefig("camHist.png")
    plt.close()

xs, ys, zs, r2s = [], [], [], []

total = 0
badxy = 0
badr2 = 0
for curEv in reconCoords:
    for coord in curEv:
        x = coord[0][0]
        y = coord[0][1]
        z = coord[0][2]
        r2 = x**2 + y**2
        xs.append(x)
        ys.append(y)
        zs.append(z)
        r2s.append(r2)
        total += 1
        if z <= 25.4 * -8.75 - 10 or z >= 25.4 * (14.71887 - 15.358) + 10:
            badr2 += 1
        if r2 >= (25.4 * (4.525 + 0.2) + 10)**2:
            badxy += 1
print(f"Outside of y vs x bounds:\t" + str(badxy) + "/" + str(total))
print(f"Outside of z bounds:\t" + str(badr2) + "/" + str(total))

import gc
gc.collect()

xs = np.asarray(xs, dtype=np.float32)
ys = np.asarray(ys, dtype=np.float32)
zs = np.asarray(zs, dtype=np.float32)
r2s = np.asarray(r2s, dtype=np.float32)

TARGET_BIN_MM = 3.0       # physical bin width, in mm, for every heat map axis
MAX_BINS_PER_AXIS = 2000  # hard cap regardless of TARGET_BIN_MM

def mm_bin_edges(data_min, data_max, target_width_mm, max_bins=MAX_BINS_PER_AXIS):
    """Bin edges spaced at ~target_width_mm, evenly covering [data_min, data_max],
    capped at max_bins so a very small target width can't blow up memory."""
    span = max(data_max - data_min, 1e-9)
    n_bins = int(np.clip(np.ceil(span / target_width_mm), 1, max_bins))
    return np.linspace(data_min, data_max, n_bins + 1)

def hist2d_counts(a, b, a_edges, b_edges):
    """2D histogram as float32 counts, returned already transposed to the
    (rows=b, cols=a) shape pcolormesh expects. Computing this once (instead
    of rebuilding it per figure) is what avoids the duplicate multi-hundred-
    MB allocations the old code made for every heat map."""
    counts, _, _ = np.histogram2d(a, b, bins=[a_edges, b_edges])
    return counts.T.astype(np.float32)

x_edges_xy = mm_bin_edges(xs.min(), xs.max(), TARGET_BIN_MM)
y_edges = mm_bin_edges(ys.min(), ys.max(), TARGET_BIN_MM)
z_edges = mm_bin_edges(zs.min(), zs.max(), TARGET_BIN_MM)
x_edges_xz = x_edges_xy

countsxy = hist2d_counts(xs, ys, x_edges_xy, y_edges)
countsxz = hist2d_counts(xs, zs, x_edges_xz, z_edges)

r2mask = (zs <= 50) & (r2s >= 2500)
r2s_mask = r2s[r2mask]
zs_mask = zs[r2mask]

r_mask = np.sqrt(np.clip(r2s_mask, 0, None))          # mm^2 -> mm
r_edges = mm_bin_edges(r_mask.min(), r_mask.max(), TARGET_BIN_MM)
r2_edges = r_edges ** 2                                # mm -> mm^2 (non-uniform spacing)
z_edges_r2 = mm_bin_edges(zs_mask.min(), zs_mask.max(), TARGET_BIN_MM)

countsr2 = hist2d_counts(r2s_mask, zs_mask, r2_edges, z_edges_r2)

del r2mask, r2s_mask, zs_mask, r_mask
gc.collect()

def draw_xy_guides(ax):
    theta = np.linspace(0, 2*np.pi, 400)
    ax.plot(25.4*4.525*np.cos(theta), 25.4*4.525*np.sin(theta), c='r')
    ax.plot(25.4*(4.525+0.2)*np.cos(theta), 25.4*(4.525+0.2)*np.sin(theta), c='r')

def draw_xz_guides(ax):
    ax.vlines(25.4*4.525, 25.4*-8.75, 25.4*(14.71997 - 15.358), color='r')
    ax.vlines(25.4*-4.525, 25.4*-8.75, 25.4*(14.71997 - 15.358), color='r')
    ax.vlines(25.4*4.725, 25.4*-8.75, 25.4*(14.71997 - 15.358), color='r')
    ax.vlines(25.4*(-4.725), 25.4*-8.75, 25.4*(14.71997 - 15.358), color='r')

    theta = np.linspace(0, 1.19367, 400)
    rcirc = 2 * 25.4
    xcirc = rcirc * np.cos(theta) + 25.4*2.725
    ycirc = rcirc * np.sin(theta) + 25.4*(14.71997 - 15.358)
    ax.plot(xcirc, ycirc, c='r')
    theta = np.linspace(0, 1.19367, 400)
    rcirc = 2*25.4 - 25.4*0.2
    xcirc = rcirc * np.cos(theta) + 25.4*2.725
    ycirc = rcirc * np.sin(theta) + 25.4*(14.71997 - 15.358)
    ax.plot(xcirc, ycirc, c='r')
    theta = np.linspace(np.pi - 1.19367, np.pi, 400)
    rcirc = 2 * 25.4
    xcirc = rcirc * np.cos(theta) - 25.4*2.725
    ycirc = rcirc * np.sin(theta) + 25.4*(14.71997 - 15.358)
    ax.plot(xcirc, ycirc, c='r')
    theta = np.linspace(np.pi - 1.19367, np.pi, 400)
    rcirc = 2 * 25.4 - 25.4*0.2
    xcirc = rcirc * np.cos(theta) - 25.4*2.725
    ycirc = rcirc * np.sin(theta) + 25.4*(14.71997 - 15.358)
    ax.plot(xcirc, ycirc, c='r')
    theta = np.linspace(1.19367, np.pi-1.19367, 400)
    rcirc = 9.4 * 25.4
    xcirc = rcirc * np.cos(theta)
    ycirc = rcirc * np.sin(theta) + 25.4*(7.84 - 15.358)
    ax.plot(xcirc, ycirc, c='r')
    theta = np.linspace(1.19367, np.pi-1.19367, 400)
    rcirc = 9.4 * 25.4 - 25.4*0.2
    xcirc = rcirc * np.cos(theta)
    ycirc = rcirc * np.sin(theta) + 25.4*(7.84 - 15.358)
    ax.plot(xcirc, ycirc, c='r')

def draw_r2z_guides(ax):
    ax.vlines((25.4*4.525)**2, 25.4*-8.75, 25.4*(14.71997 - 15.358), color='r')
    ax.vlines((25.4*4.725)**2, ymin=25.4*-8.75, ymax=25.4*(14.71997 - 15.358), color='r')

    theta = np.linspace(0, 1.19367, 400)
    rcirc = 2 * 25.4
    ax.plot((rcirc*np.cos(theta)+25.4*2.725)**2,
            rcirc*np.sin(theta)+25.4*(14.71997-15.358), c='r')

    rcirc = 1.8 * 25.4
    ax.plot((rcirc*np.cos(theta)+25.4*2.725)**2,
            rcirc*np.sin(theta)+25.4*(14.71997-15.358), c='r')

fig = plt.figure(figsize=(8, 8), constrained_layout=True)
gs = fig.add_gridspec(nrows=3, ncols=2, height_ratios=[1, 1, 1])

ax1 = fig.add_subplot(gs[0, 0])  # y vs x
ax2 = fig.add_subplot(gs[0, 1])  # x vs z
ax3 = fig.add_subplot(gs[2, :])  # r2 vs z

for ax in (ax1, ax2, ax3):
    ax.set_aspect('equal', adjustable='box')
    ax.grid(True)

draw_xy_guides(ax1)
p1 = ax1.pcolormesh(x_edges_xy, y_edges, countsxy, shading="auto", cmap="viridis")
plt.colorbar(p1, label="Bubble count", ax=ax1)
ax1.set_xlabel("x (mm)")
ax1.set_ylabel("y (mm)")
ax1.set_title("y vs x")
ax1.set_xlim(-5 * 25.4, 5 * 25.4)
ax1.set_ylim(-5 * 25.4, 5 * 25.4)

draw_xz_guides(ax2)
p2 = ax2.pcolormesh(x_edges_xz, z_edges, countsxz, shading="auto", cmap="viridis")
plt.colorbar(p2, label="Bubble count", ax=ax2)
ax2.set_xlabel("x (mm)")
ax2.set_ylabel("z (mm)")
ax2.set_title("z vs x")
ax2.set_xlim(0, 200)
ax2.set_ylim(-250, 100)

draw_r2z_guides(ax3)
p3 = ax3.pcolormesh(r2_edges, z_edges_r2, countsr2, shading="auto", cmap="viridis")
plt.colorbar(p3, label="Bubble count", ax=ax3)
ax3.set_xlabel("r2 (mm^2)")
ax3.set_ylabel("z (mm)")
ax3.set_xlim(2500, 20000)
ax3.set_ylim(-300, 50)
ax3.set_title("r2 vs z")
ax3.set_aspect('auto')

plt.savefig("triheat.png")
plt.close(fig)


fig, ax = plt.subplots()
draw_xy_guides(ax)
mesh = ax.pcolormesh(x_edges_xy, y_edges, countsxy, shading="auto", cmap="viridis")
plt.colorbar(mesh, label="Bubble count", ax=ax)
ax.set_xlabel("x (mm)")
ax.set_ylabel("y (mm)")
ax.set_title("y vs x")
ax.set_xlim(-5 * 25.4, 5 * 25.4)
ax.set_ylim(-5 * 25.4, 5 * 25.4)
ax.grid(True)
plt.savefig("recoYxX.png")
plt.close(fig)

fig, ax = plt.subplots()
draw_xz_guides(ax)
mesh = ax.pcolormesh(x_edges_xz, z_edges, countsxz, shading="auto", cmap="viridis")
plt.colorbar(mesh, label="Bubble count", ax=ax)
ax.set_xlabel("x (mm)")
ax.set_ylabel("z (mm)")
ax.set_title("z vs x")
ax.set_xlim(0, 200)
ax.set_ylim(-250, 100)
ax.grid(True)
plt.savefig("recoZvX.png")
plt.close(fig)

fig, ax = plt.subplots()
draw_r2z_guides(ax)
mesh = ax.pcolormesh(r2_edges, z_edges_r2, countsr2, shading="auto", cmap="viridis")
plt.colorbar(mesh, label="Bubble count", ax=ax)
ax.set_xlabel("r2 (mm^2)")
ax.set_ylabel("z (mm)")
ax.set_xlim(2500, 20000)
ax.set_ylim(-300, 50)
ax.set_title("r2 vs z")
ax.grid(True)
plt.savefig("recoR2vZ.png")
plt.close(fig)
