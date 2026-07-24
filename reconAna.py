# imports
import sys, os
import matplotlib
# force the non-interactive backend: this script only ever calls savefig, and
# forking worker processes after a GUI backend (e.g. TkAgg) has been touched
# leads to tkinter cleanup errors in the child processes at exit.
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sbcbinaryformat import Streamer, Writer
from concurrent.futures import ProcessPoolExecutor

# 2d to 3d to 2d math

def backTo2d(P,x):
    x = x /25.4
    X_h = np.append(x,1.0)
    proj = P @ X_h
    proj = proj[:2] /proj[2]
    return proj

# projection matricies for the 3 cameras - populated in the __main__ block below,
# and copied into each worker process by _initWorker so grabCoords can see it
# whichever process it runs in (fork or spawn).
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
    #ax.set_xlim(-500,900)
    #ax.set_ylim(-500,1400)
    ax.set_xlabel('x (pixels)')
    ax.set_ylabel('y (pixels)')
    ax.invert_yaxis()

# settings used by the bin edge helper below
if not FIRST_PAIR_ONLY:
    TARGET_BIN_MM = 10.0       # physical bin width, in mm, for every heat map axis
    MAX_BINS_PER_AXIS = 20000  # hard cap regardless of TARGET_BIN_MM
else:
    TARGET_BIN_MM = 5.0       # physical bin width, in mm, for every heat map axis
    MAX_BINS_PER_AXIS = 20000  # hard cap regardless of TARGET_BIN_MM

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


# Everything below has side effects (reads argv, spawns worker processes, writes
# files) so it's guarded by __main__ - required for multiprocessing to work
# correctly regardless of whether the platform uses fork or spawn to start workers.
if __name__ == "__main__":
    # grab files
    if len(sys.argv) != 3:
        print("Usage: reconTest.py <path to reco version> <path to output> ", file=sys.stderr)
        sys.exit(2)
    recover = sys.argv[1]
    root = sys.argv[2]
    if not os.path.exists(root):
        print(f"Path does not exist: {root}", file=sys.stderr)
        sys.exit(2)

    # grab reco.py
    # helper to pull a function out of a python file by path, without a normal import
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
    # load the getProjMat function from the given reco version
    getProjMat = loadModule(recover, "getProjMat")

    # grab the projection matrix for each of the 3 cameras
    projMatricies.append(getProjMat(1))
    projMatricies.append(getProjMat(2))
    projMatricies.append(getProjMat(3))

    # walk the root dir and collect folders that have both a reco.sbc and bubble.sbc,
    # stop after limiter pairs. This is just a directory listing (cheap) - the actual
    # file reads/parses/grabCoords calls happen below, in parallel across processes.
    limiter = 1000
    pairPaths = []
    for dirpath, dirnames, filenames in os.walk(root):
        if "reco.sbc" in filenames and "bubble.sbc" in filenames:
            pairPaths.append((os.path.join(dirpath, "reco.sbc"), os.path.join(dirpath, "bubble.sbc")))
        if len(pairPaths) >= limiter:
            break

    # read + parse each folder's data and run grabCoords on it in a worker pool,
    # instead of doing it serially in the main process. This is what removes the
    # disk-I/O / binary-parsing time from the critical path on multi-core machines.
    originalNewSets = []
    reconCoords = []
    if pairPaths:
        with ProcessPoolExecutor(initializer=_initWorker, initargs=(projMatricies,)) as pool:
            for result in pool.map(processPair, *zip(*pairPaths)):
                if result is None:
                    continue
                setsToAdd, recosToAdd = result
                originalNewSets.append(setsToAdd)
                reconCoords.append(recosToAdd)
    count = len(originalNewSets)

    # only make the per-camera scatter/arrow plots and reproj error histogram if there's just one event
    if count == 1:
        # group points by camera so each subplot only gets its own cam's points
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

        # compute the reprojection error distance for every point, split by camera
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
        # build shared bins for the histogram from the full range of distances
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

    # pull x, y, z out of every reco coord and flag ones outside the detector's xy/z bounds
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

    # free up memory before building the heat maps below
    import gc
    gc.collect()

    xs = np.asarray(xs, dtype=np.float32)
    ys = np.asarray(ys, dtype=np.float32)
    zs = np.asarray(zs, dtype=np.float32)
    r2s = np.asarray(r2s, dtype=np.float32)

    # build bin edges and 2d histograms for the xy and xz heat maps
    x_edges_xy = mm_bin_edges(xs.min(), xs.max(), TARGET_BIN_MM)
    y_edges = mm_bin_edges(ys.min(), ys.max(), TARGET_BIN_MM)
    z_edges = mm_bin_edges(zs.min(), zs.max(), TARGET_BIN_MM)
    x_edges_xz = x_edges_xy

    countsxy = hist2d_counts(xs, ys, x_edges_xy, y_edges)
    countsxz = hist2d_counts(xs, zs, x_edges_xz, z_edges)

    # build the r2 vs z heat map, only using points near the target region
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

    # combined figure with all three heat maps (xy, xz, r2 vs z) side by side
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

    if FIRST_PAIR_ONLY:
        plt.savefig("triheatSingle.png")
    else:
        plt.savefig("triheatMult.png")

    plt.close(fig)


    # standalone y vs x heat map
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
    if FIRST_PAIR_ONLY:
        plt.savefig("recoYvXSingle.png")
    else:
        plt.savefig("recoYvXMult.png")
    plt.close(fig)

    # standalone z vs x heat map
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
    if FIRST_PAIR_ONLY:
        plt.savefig("recoZvXSingle.png")
    else:
        plt.savefig("recoZvXMult.png")
    plt.close(fig)

    # standalone r2 vs z heat map
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
    if FIRST_PAIR_ONLY:
        plt.savefig("recoR2vZSingle.png")
    else:
        plt.savefig("recoR2vZMult.png")
    plt.close(fig)
