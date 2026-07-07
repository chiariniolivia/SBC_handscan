# external dependences
## sys, os, tarfile, shutil is for scratch directory managment so you can extract the data then delete it afterwards
## argparse is just to make the arguments look nice and have a help command
## pyplot is for manual coordinate finding when handscaning
## warninigs is just for the output to look better
## atexit is to clear the scratch directory even if the user does an esc sequence or an error happens after untarring
import sys, os, csv, argparse, shutil, warnings, atexit
from collections import Counter, defaultdict
import matplotlib.pyplot as plt
import numpy as np

# internal dependences
from sbcbinaryformat import Streamer, Writer

# argparse stuff

parser = argparse.ArgumentParser(description="A program to assist with handscanning for the SBC. Make sure you are in the conda enviorment from LAr10Ana.")
## SBC input stuff
parser.add_argument("-r", "--run", required=True,help="The name of the run you want to analyze, assumed to be in SBC-25-daqdata or SBC-25-unpacked")
parser.add_argument("-e","--event",required=False, default=0, help="Event number for the run you are analyzing if not checking all")
parser.add_argument("-E", "--allevents", default=False, required=False, action="store_true", help="Flag to go through all events.")
## output stuff
parser.add_argument("-l", "--log", default=False, required=False,action="store_true", help="Flag to print debug messages to stdout")
parser.add_argument("-o", "--output", default=None, required=False, help="File to output csv file to.")



args = parser.parse_args()
## untar throws a warninig that is annoying so i added this to avoid that
warnings.filterwarnings("ignore", category=DeprecationWarning)


# make sure run exists, and we can write to the scratch direcotry for untaring
reconPath = '/exp/e961/data/SBC-25-recon/dev-output/' + args.run + '/' 
if not (os.path.exists(reconPath)):
    sys.exit("ERROR: The run directory in dataq or recon could not be found.")

def cleanUp():
    # cleanup function, after we define the scratchPath so that we know what directory to cleanup incase something else goes wrong
    ## mostly just deleting the scratch dir to conserve disk space and logging the exit
    if args.log:
        print("[Log] Exiting...")
## just set this function to run when an exit command is given, so that we can garuntee we conserve disk space
atexit.register(cleanUp)


# recon and bubble finder getting
bubble_finder_info = Streamer(reconPath + 'bubble.sbc')
bubble_finder_info = bubble_finder_info.to_dict()
if args.log:
    print('[Log] Found bubble.sbc')

reco_info = Streamer(reconPath + 'reco.sbc')
reco_info = reco_info.to_dict()
if args.log:
    print('[Log] Found reco.sbc')

rows = []


eventsToCheck = []
if args.allevents:
    if args.log:
        print("[Log] Indexing all events")
    for evNum in bubble_finder_info["ev"]:
        if evNum not in eventsToCheck:
            eventsToCheck.append(evNum)
else:
    eventsToCheck.append(args.event)

eventsToCheck.sort()

## finds the earliest frame assosioated with a given camera that it thinks there is a bubble in
### should probbaly add a minimum threshold or something like that
for eventNum in eventsToCheck:

    couldntFindCount= 0

    def findEarliest(camNum):
        global couldntFindCount 
        n_minSoFar = None
        f_minSoFar = 999
        for n in range(0,len(bubble_finder_info["frame"])):
                if (bubble_finder_info["frame"][n] < f_minSoFar) and (bubble_finder_info["cam"][n] == camNum) and (int(bubble_finder_info["ev"][n]) == int(eventNum)):
                    f_minSoFar = bubble_finder_info["frame"][n]
                    n_minSoFar = n
        if f_minSoFar == 999:
            couldntFindCount +=1
            #print("Could not find a bubble in event " + str(eventNum))
        return n_minSoFar


    def estBubbleCount(firstIndex, n):
        frames = bubble_finder_info["frame"]
        cams = bubble_finder_info["cam"]
        evs = bubble_finder_info["ev"]
        seq = [(f, c) for f, c, e in zip(frames, cams, evs) if (e == int(eventNum)) and ( f >= bubble_finder_info["frame"][firstIndex] and f <= bubble_finder_info["frame"][firstIndex] + (10 + n)) ]
        if not seq:
            return -1

        mult = Counter(seq)  # {(frame, cam): multiplicity}
        byCamDict = defaultdict(dict)
        lastSeen = set()
        for f, c in seq:
            if (f,c) not in lastSeen:
                byCamDict[c][f] = mult[(f,c)]
                lastSeen.add((f,c)) 
   
    
        sortedByMult = sorted(mult.keys(), key = lambda k: mult[k], reverse=True)
        checked  = []
        for f0, c0 in sortedByMult:
            if ( (f0,c0) in checked):
                continue
            #if ((f0,1) not in sortedByMult) or ((f0,2) not in sortedByMult) or ((f0,3) not in sortedByMult):
            #    print("hey this is an outlier maybe")
            checked.append((f0,c0))
            m0 = mult[(f0,c0)]
            #print(m0)
            ok = True
            for offset in range(n):    
                if  mult[f0 + offset, c0] < mult[f0, c0]:
                    ok = False
                    break
            if ok:
                return m0

        return 0


    ## for each camera, find the earliest possible bubble, then tell the user the camera, frame, and coordinates
    #print("\n\nFor event "+str(eventNum))
    indexOfFirstCam1=findEarliest(1)
    indexOfFirstCam2=findEarliest(2)
    indexOfFirstCam3=findEarliest(3)
    
    if couldntFindCount == 3:
        print("No bubbles where found for "+ args.run +" during event " + eventNum +" for any camera. Exiting.")
        exit(1)
    rows.append([args.run,eventNum, -1, 99, np.asarray([-1,-1]), 99, [-1,-1], 99, [-1,-1], -1, -1 ])
    if not (indexOfFirstCam1 is None):
        rows[-1][3]=bubble_finder_info["frame"][indexOfFirstCam1]
        rows[-1][4]=(bubble_finder_info["pos"][indexOfFirstCam1])
    if not (indexOfFirstCam2 is None):
        rows[-1][5]=bubble_finder_info["frame"][indexOfFirstCam2]
        rows[-1][6]=(bubble_finder_info["pos"][indexOfFirstCam2])
    if not (indexOfFirstCam3 is None):
        rows[-1][7]=bubble_finder_info["frame"][indexOfFirstCam3]
        rows[-1][8]=(bubble_finder_info["pos"][indexOfFirstCam3])
            
    if indexOfFirstCam1 is None:
        indexOfFirstCam1=-1
    if indexOfFirstCam2 is None:
        indexOfFirstCam2=-1
    if indexOfFirstCam3 is None:
        indexOfFirstCam3=-1
    
    minIndex = max(indexOfFirstCam1, indexOfFirstCam2,indexOfFirstCam3)
    rows[-1][2]=estBubbleCount(minIndex,3)

    event_analysis = Streamer("/exp/e961/data/SBC-25-unpacked/"+args.run+ "/"+str(eventNum) +"/event_info.sbc")
    event_analysis = event_analysis.to_dict()
    rows[-1][-2] = event_analysis["pset_lo"][0]

    rows[-1][-1] = event_analysis["ev_livetime"][0]/1000
header= ["run","event","numBubbles","cam1First","cam1Cord","cam2First","cam2Cord","cam3First","cam3Cord","pset","evlivetime"]

csvPath = args.output
if csvPath is None:
    csvPath = args.run+ ".csv"
file_exists = os.path.isfile(csvPath)
with open(csvPath, 'a', newline='\n', encoding='utf-8') as f:
    writer = csv.writer(f)
    if not file_exists:
        writer.writerow(header)
    for row in rows:
        writer.writerow(row)

exit()
