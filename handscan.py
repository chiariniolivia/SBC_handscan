# external dependences
## sys, os, tarfile, shutil is for scratch directory managment so you can extract the data then delete it afterwards
## argparse is just to make the arguments look nice and have a help command
## pyplot is for manual coordinate finding when handscaning
import sys, os, argparse, tarfile,shutil
import matplotlib.pyplot as plt
# internal dependences
from sbcbinaryformat import Streamer, Writer

# argparse stuff


parser = argparse.ArgumentParser(description="A program to assist with handscanning for the SBC. Make sure you are in the conda enviorment from LAr10Ana.")
parser.add_argument("-e", "--event", required=True,help="The name of the event you want to analyze, assumed to be in SBC-25-daqdata")
parser.add_argument("-s", "--scratch", required=False, default='.', help="Directory to do scratch work in i.e. untar data")
parser.add_argument("-l", "--log", required=False, type=bool, default=True, help="Bool to print debug messages")
args = parser.parse_args()

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
## TODO: pull out cam, pos, earliest frame
if args.log:
    print('Found bubble.sbc')

# handscan stuff
with tarfile.open(dataPath) as tar:
    tar.extractall(scratchPath)
    tar.close()



# cleanup
## mostly just deleting the scratch dir to conserve disk space
shutil.rmtree(scratchPath)

