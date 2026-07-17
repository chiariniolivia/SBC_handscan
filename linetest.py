import sys, os
import matplotlib.pyplot as plt
import numpy as np
from sbcbinaryformat import Streamer, Writer





def getProjMat(camNum):
    '''
    camNum: 1,2, or3
    Returns:
        4x3 matrix or np.nan if invalid camera
    '''
    if camNum == 1:
        return np.array([[-1.05302109e+02, -7.02444185e+02, -3.34577970e+02,  5.72535995e+03],
                [-5.51213766e+02,  2.58404210e+01, -3.45420423e+02,  3.46877200e+03],
                [ 5.46200003e-02, -3.31725499e-01, -9.41793422e-01,  8.93247437e+00]])


    if camNum == 2:
        return np.array([[ 6.24551374e+02,  2.05426176e+02, -4.20327029e+02,  6.08648299e+03],
                [ 2.38142395e+02, -5.16479247e+02, -3.98154885e+02,  3.57897785e+03],
                [ 1.75014306e-01,  8.21425255e-02, -9.81133323e-01,  8.45879059e+00]])

    
    if camNum == 3:
        return np.array([[-4.46470566e+02,  4.77173422e+02, -4.42541834e+02,  5.80637791e+03],
                [ 3.67166284e+02,  4.75216795e+02, -4.43358757e+02,  3.38952193e+03],
                [-9.35610736e-02,  1.48157021e-01, -9.84528223e-01,  7.62754209e+00]])
    return np.array([[np.nan,  np.nan, np.nan,  np.nan],
     [np.nan, np.nan, np.nan, np.nan],
     [np.nan,np.nan,np.nan,np.nan]])

evList = []


# [cam1x cam1y cam2x cam2y cam3x cam3y]
## 20251125_6/29, frame 5
bubbleList = []
bubbleList.append((130,87,188,74, np.nan, np.nan))
bubbleList.append((128,89,183,74, np.nan, np.nan))
bubbleList.append((125,90,173,77, np.nan, np.nan))
evList.append(bubbleList)

## 20251125_7/44, frame 5
bubbleList = []
bubbleList.append((295,602,443,759,486,692))
bubbleList.append((330,564,410,719,501,670))
bubbleList.append((404,489,344,625,508,656))
evList.append(bubbleList)

## 20251125_8/3, frame 5
## weird case w/4 bubbles and 3 in a row. might as well reco all of them.
bubbleList = []
## association is hard here, doing my best.
## wall bubble
bubbleList.append((647,613,np.nan,np.nan,390,965))
## closest to spider vein
bubbleList.append((460,640,np.nan,np.nan,295,570))
## closest to SiPM
bubbleList.append((403,664,np.nan,np.nan,362,736))
## other one 
bubbleList.append((414,633,np.nan,np.nan,340,630))
evList.append(bubbleList)

## 20251125_8/84, frame 14
bubbleList = []
bubbleList.append((612,736,np.nan,np.nan,240,884))
bubbleList.append((621,658,np.nan,np.nan,286,875))
bubbleList.append((579,527,np.nan,np.nan,375,811))
evList.append(bubbleList)








def triangulate_multi_cam_LS(pixel_coords):
    '''
    pixel_coords: [cam1x,cam1y,cam2x,cam2y,cam3x,cam3y] with np.nan where missing cam

    Returns:
        3D point (X,Y,Z) or np.nan if not enough defined points
    '''

    P1 = getProjMat(1)
    P2 = getProjMat(2)
    P3 = getProjMat(3)

    P_mats = [P1, P2, P3]

    pixel_coords = np.asarray(pixel_coords).reshape(3, 2)
    A = []
    valid_cam_count = 0

    for P, (x, y) in zip(P_mats, pixel_coords):

        # Skip camera if either coordinate is np.nan
        if np.isnan(x) or np.isnan(y):
            continue
        valid_cam_count += 1

        A.append(x * P[2] - P[0])
        A.append(y * P[2] - P[1])

    # if there isnt 2 or more cameras, we cant triangulate
    if valid_cam_count < 2:
        return np.array([np.nan,np.nan, np.nan])

    A = np.array(A)

    _, _, Vt = np.linalg.svd(A)
    X = Vt[-1]
    X = X / X[3]
    return X[:3] * 25.4

sets3d = []
cam1xs = []
cam2xs = []
cam3xs = []
cam1ys = []
cam2ys = []
cam3ys = []
for ev in evList:
    curSet = []
    for coord in ev:
        cam1xs.append(coord[1])
        cam1ys.append(coord[0])
        cam2xs.append(coord[3])
        cam2ys.append(coord[2])
        cam3xs.append(coord[5])
        cam3ys.append(coord[4])
        coordToReco = (coord[1], coord[0], coord[3], coord[2], coord[5], coord[4])
        curSet.append(triangulate_multi_cam_LS(coordToReco))
    sets3d.append(curSet)

# reco plotting
xs,ys, zs, r2s = [], [], [], []
i = 0
colorIndex = []

colors = ["teal", "purple", "blue", "green", "orange", "red", "yellow"]
for ev in sets3d:
    for coord in ev:
        x = coord[0]/10
        y = coord[1]/10
        z = coord[2]/10
        r2 = x**2 + y**2
        xs.append(x)
        ys.append(y)
        zs.append(z)
        r2s.append(r2)
        colorIndex.append(i)
    i += 1

xs = np.asarray(xs)
ys = np.asarray(ys)
zs = np.asarray(zs)
r2s = np.asarray(r2s)

# resolution
nx, ny = int(len(xs)/10),int(len(xs)/10)

# y vs x
theta = np.linspace(0, 2*np.pi, 400)
plt.plot(11.4935*np.cos(theta), 11.4935*np.sin(theta), c='r')
plt.plot((12.0015)*np.cos(theta), (12.0015)*np.sin(theta), c='r')

plt.scatter(xs[:3],ys[:3], color=colors[colorIndex[0]], label="20251125_6/29")
plt.scatter(xs[3:6],ys[3:6], color=colors[colorIndex[3]], label="20251125_7/44")
plt.scatter(xs[6:10],ys[6:10], color=colors[colorIndex[6]], label="20251125_8/3")
plt.scatter(xs[10:13],ys[10:13], color=colors[colorIndex[10]], label="20251125_8/84")

plt.xlabel("x (cm)")
plt.ylabel("y (cm)")
plt.title("y vs x")
plt.legend(loc="upper right")
plt.grid(True)
plt.tight_layout()
plt.savefig("recoYxX.png")
plt.show()
plt.close()



# x vs z
plt.vlines(11.4935,-22.225,-1.6205962,color='r')
plt.vlines(-11.4935,-22.225,-1.6205962,color='r')
plt.vlines(12.0015,-22.225,-1.6205962,color='r')
plt.vlines(-12.0015,-22.225,-1.6205962,color='r')

theta = np.linspace(0, 1.19367, 400)
rcirc = 5.08
xcirc = rcirc * np.cos(theta) + 6.9215
ycirc = rcirc * np.sin(theta) -1.6205962
plt.plot(xcirc, ycirc, c='r')
theta = np.linspace(0, 1.19367, 400)
rcirc = 4.572
xcirc = rcirc * np.cos(theta) + 6.9215
ycirc = rcirc * np.sin(theta) -1.6205962
plt.plot(xcirc, ycirc, c='r')
theta = np.linspace(np.pi - 1.19367, np.pi, 400)
rcirc = 5.08
xcirc = rcirc * np.cos(theta) - 6.9215
ycirc = rcirc * np.sin(theta) -1.6205962
plt.plot(xcirc, ycirc, c='r')
theta = np.linspace(np.pi - 1.19367, np.pi, 400)
rcirc = 4.572
xcirc = rcirc * np.cos(theta) - 6.9215
ycirc = rcirc * np.sin(theta) -1.6205962
plt.plot(xcirc, ycirc, c='r')
theta = np.linspace(1.19367, np.pi-1.19367, 400)
rcirc = 23.876
xcirc = rcirc * np.cos(theta)
ycirc = rcirc * np.sin(theta) -19.09572
plt.plot(xcirc, ycirc, c='r')
theta = np.linspace(1.19367, np.pi-1.19367, 400)
rcirc = 23.368
xcirc = rcirc * np.cos(theta)
ycirc = rcirc * np.sin(theta) -19.09572
plt.plot(xcirc, ycirc,c='r')


plt.scatter(xs[:3],zs[:3], color=colors[colorIndex[0]], label="20251125_6/29")
plt.scatter(xs[3:6],zs[3:6], color=colors[colorIndex[3]], label="20251125_7/44")
plt.scatter(xs[6:10],zs[6:10], color=colors[colorIndex[6]], label="20251125_8/3")
plt.scatter(xs[10:13],zs[10:13], color=colors[colorIndex[10]], label="20251125_8/84")

plt.legend(loc="upper right")
plt.xlabel("x (cm)")
plt.ylabel("z (cm)")
plt.title("z vs x")
plt.grid(True)
plt.savefig("recoZvX.png")
plt.tight_layout()
plt.show()
plt.close()

# r2 vs z
plt.vlines(11.4935**2,-22.225,-1.6205962,color='r')
plt.vlines(12.0015**2,ymin=-22.225,ymax=-1.6205962,color='r')

theta = np.linspace(0, 1.19367, 400)
rcirc = 5.08
plt.plot((rcirc*np.cos(theta)+6.9215)**2,
         rcirc*np.sin(theta)-1.6205962,c='r')

rcirc = 4.572
plt.plot((rcirc*np.cos(theta)+6.9215)**2,
         rcirc*np.sin(theta)-1.6205962,c='r')


plt.scatter(r2s[:3],zs[:3], color=colors[colorIndex[0]], label="20251125_6/29")
plt.scatter(r2s[3:6],zs[3:6], color=colors[colorIndex[3]], label="20251125_7/44")
plt.scatter(r2s[6:10],zs[6:10], color=colors[colorIndex[6]], label="20251125_8/3")
plt.scatter(r2s[10:13],zs[10:13], color=colors[colorIndex[10]], label="20251125_8/84")


plt.legend(loc="upper right")
plt.xlabel("r2 (cm^2)")
plt.ylabel("z (cm)")
plt.title("r2 vs z")
plt.grid(True)
plt.tight_layout()
plt.savefig("recoR2vZ.png")
plt.show()
plt.close()


# per camera plot in pixel spac
fig = plt.figure(figsize=(8,8), constrained_layout=True)
gs = fig.add_gridspec(nrows=3, ncols=2, 
                      height_ratios=[1, 1, 1]) # top row #1, top row #2, bottom row all equal height

ax1 = fig.add_subplot(gs[0, 0])
ax2 = fig.add_subplot(gs[0, 1])
ax3 = fig.add_subplot(gs[2, :])


for ax in (ax1, ax2, ax3):
    ax.invert_yaxis()
    ax.set_xlim(0, 1000) 
    ax.set_ylim(0, 1000)
    ax.set_aspect('equal', adjustable='box')
    ax.grid(True) 
    ax.set_xlabel("x (pix)")
    ax.set_ylabel("y (pix)")

ax1.set_title("Camera 1 Subplot")
ax1.scatter(cam1xs[:3],cam1ys[:3], color=colors[colorIndex[0]], label="20251125_6/29")
ax1.scatter(cam1xs[3:6],cam1ys[3:6], color=colors[colorIndex[3]], label="20251125_7/44")
ax1.scatter(cam1xs[10:13],cam1ys[10:13], color=colors[colorIndex[10]], label="20251125_8/84")
ax1.legend()

ax2.set_title("Camera 2 Subplot")
ax2.scatter(cam2xs[:3],cam2ys[:3], color=colors[colorIndex[0]], label="20251125_6/29")
ax2.scatter(cam2xs[3:6],cam2ys[3:6], color=colors[colorIndex[3]], label="20251125_7/44")
ax2.scatter(cam2xs[10:13],cam2ys[10:13], color=colors[colorIndex[10]], label="20251125_8/84")
ax2.legend()

ax3.set_title("Camera 3 Subplot")
ax3.scatter(cam3xs[:3],cam3ys[:3], color=colors[colorIndex[0]], label="20251125_6/29")
ax3.scatter(cam3xs[3:6],cam3ys[3:6], color=colors[colorIndex[3]], label="20251125_7/44")
ax3.scatter(cam3xs[10:13],cam3ys[10:13], color=colors[colorIndex[10]], label="20251125_8/84")
ax3.legend()

plt.savefig("camPos.png")
plt.show()
plt.close()

data = [1, 1, 5, 3, 2, 2, 1, 1, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 7, 3, 1, 1, 1, 1, 1, 1, 4, 1, 2, 1, 1, 2, 1, 1, 1, 5, 1, 1, 1, 1, 3, 2, 1, 1, 2, 2, 1, 1, 1, 2, 3, 2, 3, 1, 1, 1, 1, 2, 1, 1, 1, 3, 1, 2, 1, 1, 1, 1, 1, 1, 4, 4, 1, 3, 4, 1]

labels = ["1", "2", "3", "4", "5+"]
counts = [
        sum(1 for x in data if x == 1), 
        sum(1 for x in data if x == 2), 
        sum(1 for x in data if x == 3), 
        sum(1 for x in data if x == 4), 
        sum(1 for x in data if x >= 5)]

x = np.arange(len(labels))
plt.bar(x, counts, edgecolor="black")
plt.xticks(x, labels)

plt.xlabel("Multiplicity")
plt.ylabel("Count")
plt.title("In Line Multiplicity")
plt.savefig("hist.png")
plt.show()
plt.close()
