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


a = 1
b = 1
c = 1
d = 1
e = 1
f = 1

# [cam1x cam1y cam2x cam2y cam3x cam3y]
## 20251125_6/29
bubbleList = []
bubbleList.append((a,b,c,d,e,f))
bubbleList.append((a,b,c,d,e,f))
bubbleList.append((a,b,c,d,e,f))
evList.append(bubbleList)

## 20251125_7/44
bubbleList = []
bubbleList.append((a,b,c,d,e,f))
bubbleList.append((a,b,c,d,e,f))
bubbleList.append((a,b,c,d,e,f))
evList.append(bubbleList)

## 20251125_8/3
bubbleList = []
bubbleList.append((a,b,c,d,e,f))
bubbleList.append((a,b,c,d,e,f))
bubbleList.append((a,b,c,d,e,f))
evList.append(bubbleList)

## 20251125_8/84
bubbleList = []
bubbleList.append((a,b,c,d,e,f))
bubbleList.append((a,b,c,d,e,f))
bubbleList.append((a,b,c,d,e,f))
bubbleList.append((a,b,c,d,e,f))
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
for ev in evList:
    curSet = []
    for coord in ev:
        curSet.append(triangulate_multi_cam_LS(coord))
    sets3d.append(curSet)


# reco plotting
xs,ys, zs, r2s = [], [], [], []
i = 0
colorIndex = []
for ev in sets3d:
    for coord in ev:
        x = coord[0]
        y = coord[0]
        z = coord[0]
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
plt.plot(25.4*4.525*np.cos(theta), 25.4*4.525*np.sin(theta), c='r')
plt.plot(25.4*(4.525+0.2)*np.cos(theta), 25.4*(4.525+0.2)*np.sin(theta), c='r')

plt.xlabel("x (mm)")
plt.ylabel("y (mm)")
plt.title("y vs x")
plt.xlim(-5* 25.4,5 * 25.4)
plt.ylim(-5* 25.4,5* 25.4)
plt.grid(True)
plt.savefig("recoYxX.png")
plt.show()
plt.close()



# x vs z
plt.vlines(25.4*4.525,25.4*-8.75,25.4*(14.71997 - 15.358),color='r')
plt.vlines(25.4*-4.525,25.4*-8.75,25.4*(14.71997 - 15.358),color='r')
plt.vlines(25.4*4.725,25.4*-8.75,25.4*(14.71997 - 15.358),color='r')
plt.vlines(25.4*(-4.725),25.4*-8.75,25.4*(14.71997 - 15.358),color='r')

theta = np.linspace(0, 1.19367, 400)
rcirc = 2 * 25.4
xcirc = rcirc * np.cos(theta) + 25.4*2.725
ycirc = rcirc * np.sin(theta) + 25.4*(14.71997 - 15.358)
plt.plot(xcirc, ycirc, c='r')
theta = np.linspace(0, 1.19367, 400)
rcirc = 2* 25.4 - 25.4*0.2
xcirc = rcirc * np.cos(theta) +  25.4* 2.725
ycirc = rcirc * np.sin(theta) + 25.4*(14.71997 - 15.358)
plt.plot(xcirc, ycirc, c='r')
theta = np.linspace(np.pi - 1.19367, np.pi, 400)
rcirc = 2 * 25.4
xcirc = rcirc * np.cos(theta) - 25.4*2.725
ycirc = rcirc * np.sin(theta) + 25.4*(14.71997 - 15.358)
plt.plot(xcirc, ycirc, c='r')
theta = np.linspace(np.pi - 1.19367, np.pi, 400)
rcirc = 2 * 25.4 - 25.4*0.2
xcirc = rcirc * np.cos(theta) - 25.4*2.725
ycirc = rcirc * np.sin(theta) + 25.4*(14.71997 - 15.358)
plt.plot(xcirc, ycirc, c='r')
theta = np.linspace(1.19367, np.pi-1.19367, 400)
rcirc = 9.4 * 25.4
xcirc = rcirc * np.cos(theta)
ycirc = rcirc * np.sin(theta) + 25.4*(7.84 - 15.358)
plt.plot(xcirc, ycirc, c='r')
theta = np.linspace(1.19367, np.pi-1.19367, 400)
rcirc = 9.4 * 25.4- 25.4*0.2
xcirc = rcirc * np.cos(theta)
ycirc = rcirc * np.sin(theta) + 25.4*(7.84 - 15.358)
plt.plot(xcirc, ycirc,c='r')



plt.xlabel("x (mm)")
plt.ylabel("z (mm)")
plt.title("z vs x")
plt.xlim(0, 200)
plt.ylim(-250,100)
plt.grid(True)
plt.savefig("recoZvX.png")
plt.show()
plt.close()

# r2 vs z



plt.vlines((25.4*4.525)**2,25.4*-8.75,25.4*(14.71997 - 15.358),color='r')
plt.vlines((25.4*4.725)**2,ymin=25.4*-8.75,ymax=25.4*(14.71997 - 15.358),color='r')

theta = np.linspace(0, 1.19367, 400)
rcirc = 2 * 25.4
plt.plot((rcirc*np.cos(theta)+25.4*2.725)**2,
         rcirc*np.sin(theta)+25.4*(14.71997-15.358),c='r')

rcirc = 1.8 * 25.4
plt.plot((rcirc*np.cos(theta)+25.4*2.725)**2,
         rcirc*np.sin(theta)+25.4*(14.71997-15.358),c='r')



plt.xlabel("r2 (mm^2)")
plt.ylabel("z (mm)")
plt.xlim(2500,20000)
plt.ylim(-300,50)
plt.title("r2 vs z")
plt.grid(True)
plt.savefig("recoR2vZ")
plt.show()
plt.close()
