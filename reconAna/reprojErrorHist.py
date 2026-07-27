import os

import numpy as np
import matplotlib.pyplot as plt
from sbcbinaryformat import Streamer

ROOT_PATH = "/exp/e961/data/SBC-25-recon/dev-output/"   # directory to walk for reco.sbc files
LIMITER = 5000                                            # stop once this many events have a valid reprojError

firstValidErrs = []

for dirpath, dirnames, filenames in os.walk(ROOT_PATH):
    if len(firstValidErrs) >= LIMITER:
        break
    if "reco.sbc" not in filenames:
        continue

    recoData = Streamer(os.path.join(dirpath, "reco.sbc")).to_dict()
    if recoData is None:
        continue

    ev = recoData["ev"]
    reprojError = recoData["reprojError"]

    # rows grouped by event, in order of first appearance
    rowsByEvent = {}
    for i, e in enumerate(ev):
        rowsByEvent.setdefault(e, []).append(i)

    for evNum, rows in rowsByEvent.items():
        if len(firstValidErrs) >= LIMITER:
            break
        for i in rows:
            valid = reprojError[i][~np.isnan(reprojError[i])]
            if valid.size:
                firstValidErrs.append(valid[0])
                break

print(f"{len(firstValidErrs)} event(s) with a first-valid reprojError value (limiter={LIMITER}).")

firstValidErrs = np.asarray(firstValidErrs, dtype=float)

plt.figure(figsize=(8, 5))
plt.hist(firstValidErrs, bins=50, color='tab:purple', edgecolor='black', linewidth=0.3)
plt.yscale('log')
plt.xlabel('reprojError')
plt.ylabel('Count (log scale)')
plt.title('reco.sbc reprojError - first valid value per event')
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig("reprojErrorHist.png")
print("Saved reprojErrorHist.png")
