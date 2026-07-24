# Shared helpers for reconAnaParallel.py / the reconAna notebook.
#
# This lives in its own importable module (rather than being defined inline in a
# notebook cell) specifically so processPair/_initWorker can be handed to a
# multiprocessing pool safely - functions defined interactively in a notebook
# kernel are not reliably picklable across worker processes, but functions
# imported from a real module on disk are.
import os
import importlib.util
import colorsys
import hashlib
import random

import numpy as np
from sbcbinaryformat import Streamer, Writer

# cheap stand-in for a content hash: used to notice when a reco.sbc/bubble.sbc
# file has been rewritten (e.g. reprocessed) so a per-folder cache entry can be
# invalidated without re-reading the file itself.
def file_fingerprint(path):
    st = os.stat(path)
    return (st.st_mtime_ns, st.st_size)

# helper to pull a function out of a python file by path, without a normal import
def loadModule(path, moduleName):
    path = os.path.expanduser(path)
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    spec = importlib.util.spec_from_file_location(moduleName, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    func = getattr(module, moduleName)
    return func

# 2d to 3d to 2d math

def backTo2d(P,x):
    x = x /25.4
    X_h = np.append(x,1.0)
    proj = P @ X_h
    proj = proj[:2] /proj[2]
    return proj

# projection matricies for the 3 cameras - populated by the caller (see the
# notebook / reconAnaParallel.py) and copied into each worker process by
# _initWorker so grabCoords can see it whichever process it runs in.
projMatricies = []

# if true, grabCoords stops and returns after the first bubble/reco pair where both the
# bubble finder position and the reco coord are not nan and not <= -999
FIRST_PAIR_ONLY = True

# match up bubble finder and reco events/frames, then reproject the reco 3d coord back to 2d for each cam
def grabCoords(bubbleInfo,reconInfo):
    # events that show up in both the bubble finder and reco data
    reconEvSet = set(reconInfo["ev"])
    seenEvents = set()
    eventsToCheck = []
    for evNum in bubbleInfo["ev"]:
        if evNum in reconEvSet and evNum not in seenEvents:
            seenEvents.add(evNum)
            eventsToCheck.append(evNum)

    # Precompute, for every (event, frame) pair, the first valid 3D reco coord,
    # in a single O(n) pass over the reco array (row i ascending, then within-row
    # frame index j ascending - first non-nan/non-sentinel value wins).
    recoLookup = {}
    reconEv = reconInfo["ev"]
    reconFrame = reconInfo["frame"]
    coords3D = reconInfo["coords_3D"]
    nCoords = len(coords3D)
    for i in range(len(reconEv)):
        ev_i = reconEv[i]
        frameRow = reconFrame[i]
        for j in range(len(frameRow)):
            idx = i + j
            if idx >= nCoords:
                continue
            key = (ev_i, frameRow[j])
            if key in recoLookup:
                continue
            coord = coords3D[idx]
            if not (np.isnan(coord).any() or coord[0] <= -999):
                recoLookup[key] = coord

    # Precompute, for every (event, frame) pair, the ordered list of bubble
    # finder row indices, in a single O(n) grouping pass over the bubble array.
    bubbleLookup = {}
    bubbleEv = bubbleInfo["ev"]
    bubbleFrame = bubbleInfo["frame"]
    bubbleCam = bubbleInfo["cam"]
    bubblePos = bubbleInfo["pos"]
    for n in range(len(bubbleFrame)):
        key = (int(bubbleEv[n]), int(bubbleFrame[n]))
        bubbleLookup.setdefault(key, []).append(n)

    setsToReturn = []
    recoToReturn = []
    for evNum in eventsToCheck:
        for f in range(50):
            # reco should tell us if the frame is good or not
            curReco = recoLookup.get((evNum, f))
            if curReco is None:
                continue

            # list of cameras that have bubbles in this frame, deduped by
            # camera and keeping the first occurrence (same as before)
            camRows = bubbleLookup.get((int(evNum), int(f)), [])
            seenCams = set()
            iList = []
            for m in camRows:
                camVal = bubbleCam[m]
                if camVal not in seenCams:
                    seenCams.add(camVal)
                    iList.append(m)

            # if not more than one cam, who cares move on.
            if len(iList) < 2:
                continue

            oList = [(bubblePos[i], bubbleCam[i], bubbleEv[i]) for i in iList]

            # reproject the 3d reco coord back to 2d for each cam and pair it with the original bubble coord
            addedPair = False
            for o in oList:
                if FIRST_PAIR_ONLY:
                    # same not-nan / not <= -999 check used on curReco above, applied to both sides of the pair
                    bubblePosArr = np.asarray(o[0], dtype=float)
                    recoArr = np.asarray(curReco, dtype=float)
                    bubbleBad = np.isnan(bubblePosArr).any() or (bubblePosArr <= -999).any()
                    recoBad = np.isnan(recoArr).any() or (recoArr <= -999).any()
                    if bubbleBad or recoBad:
                        continue
                    setsToReturn.append((o[0], backTo2d(projMatricies[o[1]-1],curReco), o[1], o[2]))
                    addedPair = True
                    # only want one pair for this cam, stop checking other cams in this frame
                    break
                setsToReturn.append((o[0], backTo2d(projMatricies[o[1]-1],curReco), o[1], o[2]))
            if FIRST_PAIR_ONLY:
                if addedPair:
                    recoToReturn.append((curReco, evNum))
                    # got our one pair for this event, move on to the next event
                    break
            else:
                recoToReturn.append((curReco, evNum))
    return setsToReturn, recoToReturn

# runs once in each worker process, before it picks up any tasks - copies the
# already-computed projection matricies into that process's global so grabCoords
# (which is also re-created in the worker) can use them.
def _initWorker(pm):
    global projMatricies
    projMatricies = pm

# per-folder unit of work: read a reco/bubble pair off disk and run grabCoords on it.
# runs in a worker process - this is what actually gets parallelized across cores.
def processPair(recoPath, bubblePath):
    recoData = Streamer(recoPath).to_dict()
    bubbleData = Streamer(bubblePath).to_dict()
    if recoData is None or bubbleData is None:
        return None
    return grabCoords(bubbleData, recoData)

# pick a semi-random color for a given index, kept consistent across runs
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

# plot original vs reprojected points for one camera, with arrows showing the offset
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
    ax.set_xlabel('x (pixels)')
    ax.set_ylabel('y (pixels)')
    ax.invert_yaxis()

def mm_bin_edges(data_min, data_max, target_width_mm, max_bins):
    """Bin edges spaced at ~target_width_mm, evenly covering [data_min, data_max],
    capped at max_bins so a very small target width can't blow up memory."""
    span = max(data_max - data_min, 1e-9)
    n_bins = int(np.clip(np.ceil(span / target_width_mm), 1, max_bins))
    return np.linspace(data_min, data_max, n_bins + 1)

def hist2d_counts(a, b, a_edges, b_edges):
    """2D histogram as float32 counts, returned already transposed to the
    (rows=b, cols=a) shape pcolormesh expects."""
    counts, _, _ = np.histogram2d(a, b, bins=[a_edges, b_edges])
    return counts.T.astype(np.float32)

# draw the detector's xy boundary circles on top of a plot
def draw_xy_guides(ax):
    theta = np.linspace(0, 2*np.pi, 400)
    ax.plot(25.4*4.525*np.cos(theta), 25.4*4.525*np.sin(theta), c='r')
    ax.plot(25.4*(4.525+0.2)*np.cos(theta), 25.4*(4.525+0.2)*np.sin(theta), c='r')

# draw the detector's xz boundary lines/arcs on top of a plot
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

# draw the detector's r2 vs z boundary lines/arcs on top of a plot
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
