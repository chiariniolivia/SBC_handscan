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
parser.add_argument("-i", "--indices", required=False, nargs=3, type=int, default=[-1,-1,-1], help="Guess at indcies when bubble appears")
## output stuff
parser.add_argument("-R", "--recon", default=False,required=False,action="store_true", help="Flag to stop after grabbing reconsuctrion guesses.")
parser.add_argument("-l", "--log", default=False, required=False,action="store_true", help="Flag to print debug messages")
parser.add_argument("-s", "--scratch", required=False, default='.', help="Directory to do scratch work in i.e. untar data")
parser.add_argument("-k", "--keep", required=False, default=False,action="store_true", help="Flag to keep events and not clear scratch directory.")



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
## make a temp directory to untar things in that is removed when exiting unless flagged otherwise
scratchPath = scratchPath + "/handscanScratch/"
os.makedirs(scratchPath, exist_ok=True)
## if the user gave an index to look at the frames with, use that. otherwise just use the earliest possible bubble
cam1Frame = bubble_finder_info["frame"][indexOfFirstCam1]
cam2Frame = bubble_finder_info["frame"][indexOfFirstCam2]
cam3Frame = bubble_finder_info["frame"][indexOfFirstCam3]
guess1, guess2,guess3 = args.indices

if  guess1 != -1 or guess2 != -1 or guess3 != -1:
    cam1Frame = guess1
    cam2Frame = guess2
    cam3Frame = guess3

try:
    ## try to open an image file, if you can then theres no need to untar the entire run again
    if args.log:
        print("[Log] Checking if this is a previously extracted event")
    if int(cam1Frame) <10:
        imcam_1 = img.open(scratchPath+ args.run+"/"+str(args.event)+"/cam1-img0"+str(cam1Frame)+".png").convert("L")
    else:
        imcam_1 = img.open(scratchPath+ args.run+"/"+str(args.event)+"/cam1-img"+str(cam1Frame)+".png").convert("L")
except:
    ## didnt find it, so untar
    if args.log:
        print("[Log] Did not find, untaring...")
    with tarfile.open(dataPath) as tar:
        tar.extractall(scratchPath)
        tar.close()

imcam_1 = None
imcam_2 = None
imcam_3 = None

if int(cam1Frame) <10:
    imcam_1 = img.open(scratchPath+ args.run+"/"+str(args.event)+"/cam1-img0"+str(cam1Frame)+".png").convert("L")
else:
    imcam_1 = img.open(scratchPath+ args.run+"/"+str(args.event)+"/cam1-img"+str(cam1Frame)+".png").convert("L")
if int(cam2Frame) <10:
    imcam_2 = img.open(scratchPath+ args.run+"/"+str(args.event)+"/cam2-img0"+str(cam2Frame)+".png").convert("L")
else:
    imcam_2 = img.open(scratchPath+ args.run+"/"+str(args.event)+"/cam2-img"+str(cam2Frame)+".png").convert("L")
if int(cam3Frame) <10:
    imcam_3 = img.open(scratchPath+ args.run+"/"+str(args.event)+"/cam3-img0"+str(cam3Frame)+".png").convert("L")
else:
    imcam_3 = img.open(scratchPath+ args.run+"/"+str(args.event)+"/cam3-img"+str(cam3Frame)+".png").convert("L")


## in theorey i should do the diff frame  here but its fine for now
###frame0 = img.open(scratchPath+ args.event+"/0/cam1-img00.png").convert("L") 
###im = im - frame0

if (args.log):
    print("[Log] Found all 3 images.")

# display all images one by one at their respective frame indicies
fig = plt.figure()
plt.imshow(imcam_1,cmap='grey')
plt.title("Cam 1 for " + args.run + " during event "+ str(args.event) +" at frame " + str(cam1Frame))
plt.show()

plt.imshow(imcam_2,cmap='grey')
plt.title("Cam 2 for " + args.run + " during event "+ str(args.event) +" at frame " + str(cam2Frame))
plt.show()

plt.imshow(imcam_3,cmap='grey')
plt.title("Cam 3 for " + args.run + " during event "+ str(args.event) +" at frame " + str(cam3Frame))
plt.show()

# cleanup
## mostly just deleting the scratch dir to conserve disk space

if not (args.keep):
    if (args.log):
        print("[Log] Cleaning up scratch directory.")
        shutil.rmtree(scratchPath)
