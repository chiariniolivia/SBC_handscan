# external dependences
## sys, os, tarfile, shutil is for scratch directory managment so you can extract the data then delete it afterwards
## argparse is just to make the arguments look nice and have a help command
## pyplot is for manual coordinate finding when handscaning
import sys, os, argparse, tarfile,shutil
from PIL import Image as img
import matplotlib.pyplot as plt
import numpy as np
import warnings
# internal dependences
from sbcbinaryformat import Streamer, Writer

# argparse stuff


parser = argparse.ArgumentParser(description="A program to assist with handscanning for the SBC. Make sure you are in the conda enviorment from LAr10Ana.")
parser.add_argument("-e", "--event", required=True,help="The name of the event you want to analyze, assumed to be in SBC-25-daqdata")
parser.add_argument("-s", "--scratch", required=False, default='.', help="Directory to do scratch work in i.e. untar data")
parser.add_argument("-i", "--index", required=False, default=-1, help="Guess at index when bubble appears")
parser.add_argument("-r", "--recon", default=False,required=False,action="store_true", help="Flag to stop after grabbing reconsuctrion guesses.")
parser.add_argument("-l", "--log", default=False, required=False,action="store_true", help="Flag to print debug messages")

args = parser.parse_args()
warnings.filterwarnings("ignore", category=DeprecationWarning)

# make sure event exists, and we can write to the scratch direcotry for untaring
reconPath = '/exp/e961/data/SBC-25-recon/dev-output/' + args.event + '/' 
dataPath = '/exp/e961/data/SBC-25-daqdata/' + args.event + '.tar'
scratchPath = args.scratch
if (not (os.path.exists(reconPath)) or not (os.path.exists(dataPath)) or not (os.path.exists(scratchPath))):
    sys.exit("ERROR: The event directory in dataq or recon could not be found.")
if not (os.access(scratchPath, os.W_OK)):
    sys.exit("ERROR: The scratch directory cannot be written in")

scratchPath = scratchPath + "/handscanScratch/"
os.makedirs(scratchPath, exist_ok=True)

# recon and bubble finder stuff
bubble_finder_info = Streamer(reconPath + 'bubble.sbc')
bubble_finder_info = bubble_finder_info.to_dict()
if args.log:
    print('[Log] Found bubble.sbc')

reco_info = Streamer(reconPath + 'reco.sbc')
reco_info = reco_info.to_dict()
if args.log:
    print('[Log] Found reco.sbc')

## TODO: pull out cam, pos, earliest frame
"""
    find lowest index in bubble_finder that says there is a bubble
    print the coordinates of said bubble
    print the camera this is in
    repeat for cameras 2 and 3
    print earliest frame

"""


def findEarliest(camNum):
    n_minSoFar = 0
    f_minSoFar = 100
    for n in range(0,len(bubble_finder_info["frame"])):
            if (bubble_finder_info["frame"][n] < f_minSoFar) and (bubble_finder_info["cam"][n] == camNum):
                f_minSoFar = bubble_finder_info["frame"][n]
                n_minSoFar = n
    return n_minSoFar

indexOfFirstCam1=findEarliest(1)
print(bubble_finder_info["frame"][indexOfFirstCam1])
print(f'Cam 1 earliest guess:\n Pos:\t{bubble_finder_info["pos"][indexOfFirstCam1]}\nEarliest Frame:\t{bubble_finder_info["frame"][indexOfFirstCam1]}')

indexOfFirstCam2=findEarliest(2)
print(bubble_finder_info["frame"][indexOfFirstCam2])
print(f'Cam 2 earliest guess:\n Pos:\t{bubble_finder_info["pos"][indexOfFirstCam2]}\nEarliest Frame:\t{bubble_finder_info["frame"][indexOfFirstCam2]}')

indexOfFirstCam3=findEarliest(3)
print(bubble_finder_info["frame"][indexOfFirstCam3])
print(f'Cam 3 earliest guess:\n Pos:\t{bubble_finder_info["pos"][indexOfFirstCam3]}\nEarliest Frame:\t{bubble_finder_info["frame"][indexOfFirstCam3]}')


if args.recon:
    exit()


# handscan stuff
if args.log:
    print("[Log] untaring...")
with tarfile.open(dataPath) as tar:
    tar.extractall(scratchPath)
    tar.close()

imcam_1 = None
imcam_2 = None
imcam_3 = None
if int(args.index) != -1:
    frameToUse = str(args.index)
    indexOfFirstCam1 = frameToUse
    indexOfFirstCam2 = frameToUse
    indexOfFirstCam3 = frameToUse
else:
    indexOfFirstCam1 = bubble_finder_info["frame"][indexOfFirstCam1]
    indexOfFirstCam2 = bubble_finder_info["frame"][indexOfFirstCam2]
    indexOfFirstCam3 = bubble_finder_info["frame"][indexOfFirstCam3]

if int(indexOfFirstCam1) <10:
    imcam_1 = img.open(scratchPath+ args.event+"/0/cam1-img0"+str(indexOfFirstCam1)+".png").convert("L")
else:
    imcam_1 = img.open(scratchPath+ args.event+"/0/cam1-img"+str(indexOfFirstCam1)+".png").convert("L")
if int(indexOfFirstCam2) <10:
    imcam_2 = img.open(scratchPath+ args.event+"/0/cam2-img0"+str(indexOfFirstCam2)+".png").convert("L")
else:
    imcam_2 = img.open(scratchPath+ args.event+"/0/cam2-img"+str(indexOfFirstCam2)+".png").convert("L")
if int(indexOfFirstCam3) <10:
    imcam_3 = img.open(scratchPath+ args.event+"/0/cam3-img0"+str(indexOfFirstCam3)+".png").convert("L")
else:
    imcam_3 = img.open(scratchPath+ args.event+"/0/cam3-img"+str(indexOfFirstCam3)+".png").convert("L")


## in theorey i should do the subtraction thing here but its fine.
#frame0 = img.open(scratchPath+ args.event+"/0/cam1-img00.png").convert("L") 
#im = im - frame0
if (args.log):
    print("[Log] Found all 3 cameras.")

# display
fig = plt.figure()
plt.imshow(imcam_1,cmap='grey')
plt.title("Cam 1 for " + args.event + " at frame " + str(indexOfFirstCam1))
plt.show()

plt.imshow(imcam_2,cmap='grey')
plt.title("Cam 2 for " + args.event + " at frame " + str(indexOfFirstCam2))
plt.show()

plt.imshow(imcam_3,cmap='grey')
plt.title("Cam 3 for " + args.event + " at frame " + str(indexOfFirstCam3))
plt.show()

# cleanup
## mostly just deleting the scratch dir to conserve disk space

if (args.log):
    print("[Log] Cleaning up scratch directory.")

shutil.rmtree(scratchPath)

