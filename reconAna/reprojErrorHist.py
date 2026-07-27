import os

import numpy as np
import matplotlib.pyplot as plt
from sbcbinaryformat import Streamer

ROOT_PATH = "/exp/e961/data/SBC-25-recon/v0.3.0/"   # directory to walk for reco.sbc files
LIMITER = 50000000                                    # stop once this many events have a valid reprojError

USE_FIRST_VALID_ONLY = True   # True: only the first valid reprojError per event. False: every valid entry per event.

# same outermost-band bounds as the notebook's "Detector bounds check" cell -
# inside the outer xy circle (+10mm margin) and between the outer z margins
def in3DRegion(coord):
    x, y, z = coord
    r2 = x**2 + y**2
    zGood = 25.4 * -8.75 - 10 < z < 25.4 * (14.71887 - 15.358) + 10
    xyGood = r2 < (25.4 * (4.525 + 0.2) + 10)**2
    return zGood and xyGood

collected = []   # (reprojError value, coords_3D coord) pairs
eventsProcessed = 0

for dirpath, dirnames, filenames in os.walk(ROOT_PATH):
    if eventsProcessed >= LIMITER:
        break
    if "reco.sbc" not in filenames:
        continue

    recoData = Streamer(os.path.join(dirpath, "reco.sbc")).to_dict()
    if recoData is None:
        continue

    ev = recoData["ev"]
    reprojError = recoData["reprojError"]
    coords3D = recoData["coords_3D"]

    # rows grouped by event, in order of first appearance
    rowsByEvent = {}
    for i, e in enumerate(ev):
        rowsByEvent.setdefault(e, []).append(i)

    for evNum, rows in rowsByEvent.items():
        if eventsProcessed >= LIMITER:
            break
        usedEvent = False
        for i in rows:
            valid = reprojError[i][(~np.isnan(reprojError[i]))]
            coord = coords3D[i]
            if not valid.size or coord[0] <= -998:
                continue
            usedEvent = True
            if USE_FIRST_VALID_ONLY:
                collected.append((valid[0], coord))
                break
            for v in valid:
                collected.append((v, coord))
        if usedEvent:
            eventsProcessed += 1

print(f"Using first-valid-only mode: {USE_FIRST_VALID_ONLY}")
print(f"{eventsProcessed} event(s) processed, {len(collected)} reprojError value(s) collected (limiter={LIMITER}).")

errs = np.array([c[0] for c in collected], dtype=float)
coords = np.array([c[1] for c in collected], dtype=float)

inRegionMask = np.array([in3DRegion(c) for c in coords], dtype=bool)
inRegionErrs = errs[inRegionMask]
outRegionErrs = errs[~inRegionMask]
pctOutRegion = 100 * outRegionErrs.size / errs.size if errs.size else 0.0
print(f"{outRegionErrs.size}/{errs.size} value(s) ({pctOutRegion:.2f}%) fell outside the defined 3D region.")

MAX_REPROJ_ERR = 50   # pixels - only applied to the in-region histogram

inRange = inRegionErrs[inRegionErrs <= MAX_REPROJ_ERR]
excluded = inRegionErrs.size - inRange.size
pctExcluded = 100 * excluded / inRegionErrs.size if inRegionErrs.size else 0.0
print(f"{excluded}/{inRegionErrs.size} in-region value(s) excluded ({pctExcluded:.2f}%) for reprojError > {MAX_REPROJ_ERR} px.")

plt.figure(figsize=(8, 5))
plt.hist(inRange, bins=50, range=(0, MAX_REPROJ_ERR), color='tab:purple', edgecolor='black', linewidth=0.3)
plt.yscale('log')
plt.xlabel('Reprojection Error (pixels)')
plt.ylabel('log Count')
plt.title('3D Reprojection Error (in region)')
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig("reprojErrorHist.png")
print("Saved reprojErrorHist.png")

plt.figure(figsize=(8, 5))
plt.hist(outRegionErrs, bins=50, color='tab:red', edgecolor='black', linewidth=0.3)
plt.xlabel('Reprojection Error (pixels)')
plt.ylabel('log Count')
plt.title('3D Reprojection Error (outside region, no pixel limit)')
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig("reprojErrorHist_outsideRegion.png")
print("Saved reprojErrorHist_outsideRegion.png")
