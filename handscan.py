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
parser.add_argument("-l", "--log", required=False, type=bool, default=True, help="Bool to print debug messages")
parser.add_argument("-i", "--index", required=False, default=0, help="Guess at index when bubble appears")
parser.add_argument("-r", "--recon", required=False, default=False, help="Bool to stop after grabbing reconsuctrion guesses.")

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
print(f'Cam 1 earliest guess:\n Pos:\t{bubble_finder_info["pos"][0]}\nEarliest Frame:\t{bubble_finder_info["frame"][0]}')

if args.recon:
    exit()


# handscan stuff
with tarfile.open(dataPath) as tar:
    tar.extractall(scratchPath)
    tar.close()
## TODO: cycle through camera 1, then 2, then 3
## in each one, allow the user to look for the first frame with a bubble
## make sure you can see the coordinates
imcam_1 = None
imcam_2 = None
imcam_3 = None
indexToUse = str(bubble_finder_info["frame"][0])
if int(args.index) != -1:
    indexToUse = str(args.index)
if int(indexToUse) < 10:
    imcam_1 = img.open(scratchPath+ args.event+"/0/cam1-img0"+indexToUse+".png").convert("L")
    imcam_2 = img.open(scratchPath+ args.event+"/0/cam2-img0"+indexToUse+".png").convert("L")
    imcam_3 = img.open(scratchPath+ args.event+"/0/cam3-img0"+indexToUse+".png").convert("L")
else:
    imcam_1 = img.open(scratchPath+ args.event+"/0/cam1-img"+indexToUse+".png").convert("L")
    imcam_2 = img.open(scratchPath+ args.event+"/0/cam2-img"+indexToUse+".png").convert("L")
    imcam_3 = img.open(scratchPath+ args.event+"/0/cam3-img"+indexToUse+".png").convert("L")
## in theorey i should do the subtraction thing here but its fine.
#frame0 = img.open(scratchPath+ args.event+"/0/cam1-img00.png").convert("L") 
#im = im - frame0
if (args.log):
    print("[Log] Found all 3 camera images at index " + indexToUse +".")

# display
fig = plt.figure()
plt.imshow(imcam_1,cmap='grey')
plt.title("Cam 1 for " + args.event + " at frame " + indexToUse)
plt.show()

plt.imshow(imcam_1,cmap='grey')
plt.title("Cam 2 for " + args.event + " at frame " + indexToUse)
plt.show()

plt.imshow(imcam_3,cmap='grey')
plt.title("Cam 3 for " + args.event + " at frame " + indexToUse)
plt.show()

# cleanup
## mostly just deleting the scratch dir to conserve disk space
if (args.log):
    print("[Log] Cleaning up scratch directory.")
shutil.rmtree(scratchPath)

