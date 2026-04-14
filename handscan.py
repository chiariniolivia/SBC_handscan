# external dependences
## sys, os, tarfile, shutil is for scratch directory managment so you can extract the data then delete it afterwards
## argparse is just to make the arguments look nice and have a help command
## pyplot is for manual coordinate finding when handscaning
## warninigs is just for the output to look better
import sys, os, argparse, tarfile,shutil, warnings
from PIL import Image as img
import matplotlib.pyplot as plt
import numpy as np

# internal dependences
from sbcbinaryformat import Streamer, Writer

# argparse stuff

parser = argparse.ArgumentParser(description="A program to assist with handscanning for the SBC. Make sure you are in the conda enviorment from LAr10Ana.")
## SBC input stuff
parser.add_argument("-r", "--run", required=True,help="The name of the run you want to analyze, assumed to be in SBC-25-daqdata")
parser.add_argument("-e","--event",required=False, default=0, help="Event number for the run you are analyzing")
parser.add_argument("-i", "--index", required=False, default=-1, help="Guess at index when bubble appears")
## output stuff
parser.add_argument("-R", "--recon", default=False,required=False,action="store_true", help="Flag to stop after grabbing reconsuctrion guesses.")
parser.add_argument("-l", "--log", default=False, required=False,action="store_true", help="Flag to print debug messages")
parser.add_argument("-s", "--scratch", required=False, default='.', help="Directory to do scratch work in i.e. untar data")

args = parser.parse_args()
## untar throws a warninig that is annoying so i added this to avoid that
warnings.filterwarnings("ignore", category=DeprecationWarning)


# make sure event exists, and we can write to the scratch direcotry for untaring
reconPath = '/exp/e961/data/SBC-25-recon/dev-output/' + args.run + '/' 
dataPath = '/exp/e961/data/SBC-25-daqdata/' + args.run + '.tar'
scratchPath = args.scratch
if (not (os.path.exists(reconPath)) or not (os.path.exists(dataPath)) or not (os.path.exists(scratchPath))):
    sys.exit("ERROR: The event directory in dataq or recon could not be found.")
if not (os.access(scratchPath, os.W_OK)):
    sys.exit("ERROR: The scratch directory cannot be written in")


# recon and bubble finder getting
bubble_finder_info = Streamer(reconPath + 'bubble.sbc')
bubble_finder_info = bubble_finder_info.to_dict()
if args.log:
    print('[Log] Found bubble.sbc')

reco_info = Streamer(reconPath + 'reco.sbc')
reco_info = reco_info.to_dict()
if args.log:
    print('[Log] Found reco.sbc')

## finds the earliest frame assosioated with a given camera that it thinks there is a bubble in
### should probbaly add a minimum threshold or something like that
def findEarliest(camNum):
    n_minSoFar = None
    f_minSoFar = 999
    for n in range(0,len(bubble_finder_info["frame"])):
            if (bubble_finder_info["frame"][n] < f_minSoFar) and (bubble_finder_info["cam"][n] == camNum) and (int(bubble_finder_info["ev"][n]) == int(args.event)):
                f_minSoFar = bubble_finder_info["frame"][n]
                n_minSoFar = n
    if f_minSoFar == 999:
        print("Could not find a bubble in event " +args.event)
        print(bubble_finder_info["frame"])
        print(bubble_finder_info["ev"])
        print(bubble_finder_info["cam"])
        exit()
    return n_minSoFar

## for each camera, find the earliest possible bubble, then tell the user the camera, frame, and coordinates

indexOfFirstCam1=findEarliest(1)
print(f'Cam 1 earliest guess:\n Pos:\t{bubble_finder_info["pos"][indexOfFirstCam1]}\nEarliest Frame:\t{bubble_finder_info["frame"][indexOfFirstCam1]}')

indexOfFirstCam2=findEarliest(2)
print(f'Cam 2 earliest guess:\n Pos:\t{bubble_finder_info["pos"][indexOfFirstCam2]}\nEarliest Frame:\t{bubble_finder_info["frame"][indexOfFirstCam2]}')

indexOfFirstCam3=findEarliest(3)
print(f'Cam 3 earliest guess:\n Pos:\t{bubble_finder_info["pos"][indexOfFirstCam3]}\nEarliest Frame:\t{bubble_finder_info["frame"][indexOfFirstCam3]}')


## if you just wanted to grab the reconscution data, then we are done here
if args.recon:
    exit()
    shutil.rmtree(scratchPath)


# handscan stuff
if args.log:
    print("[Log] untaring...")

## make a temp directory to untar things in that is removed when exiting
scratchPath = scratchPath + "/handscanScratch/"
os.makedirs(scratchPath, exist_ok=True)

with tarfile.open(dataPath) as tar:
    tar.extractall(scratchPath)
    tar.close()

imcam_1 = None
imcam_2 = None
imcam_3 = None
## if the user gave an index to look at the frames with, use that. otherwise just use the earliest possible bubble
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
    imcam_1 = img.open(scratchPath+ args.run+"/"+str(args.event)+"/cam1-img0"+str(indexOfFirstCam1)+".png").convert("L")
else:
    imcam_1 = img.open(scratchPath+ args.run+"/"+str(args.event)+"/cam1-img"+str(indexOfFirstCam1)+".png").convert("L")
if int(indexOfFirstCam2) <10:
    imcam_2 = img.open(scratchPath+ args.run+"/"+str(args.event)+"/cam2-img0"+str(indexOfFirstCam2)+".png").convert("L")
else:
    imcam_2 = img.open(scratchPath+ args.run+"/"+str(args.event)+"/cam2-img"+str(indexOfFirstCam2)+".png").convert("L")
if int(indexOfFirstCam3) <10:
    imcam_3 = img.open(scratchPath+ args.run+"/"+str(args.event)+"/cam3-img0"+str(indexOfFirstCam3)+".png").convert("L")
else:
    imcam_3 = img.open(scratchPath+ args.run+"/"+str(args.event)+"/cam3-img"+str(indexOfFirstCam3)+".png").convert("L")


## in theorey i should do the diff frame  here but its fine for now
###frame0 = img.open(scratchPath+ args.event+"/0/cam1-img00.png").convert("L") 
###im = im - frame0

if (args.log):
    print("[Log] Found all 3 images.")

# display all images one by one at their respective frame indicies
fig = plt.figure()
plt.imshow(imcam_1,cmap='grey')
plt.title("Cam 1 for " + args.run + " during event "+ str(args.event) +" at frame " + str(indexOfFirstCam1))
plt.show()

plt.imshow(imcam_2,cmap='grey')
plt.title("Cam 2 for " + args.run + " during event "+ str(args.event) +" at frame " + str(indexOfFirstCam2))
plt.show()

plt.imshow(imcam_3,cmap='grey')
plt.title("Cam 3 for " + args.run + " during event "+ str(args.event) +" at frame " + str(indexOfFirstCam3))
plt.show()

# cleanup
## mostly just deleting the scratch dir to conserve disk space

if (args.log):
    print("[Log] Cleaning up scratch directory.")

shutil.rmtree(scratchPath)
