import os
import sys
import requests
import json
import time
import re

'''
Audacity mod-script-pipeline setup
'''
# Startup audacity pipe commands
if sys.platform == 'win32':
    print("pipe-test.py, running on windows")
    TONAME = '\\\\.\\pipe\\ToSrvPipe'
    FROMNAME = '\\\\.\\pipe\\FromSrvPipe'
    EOL = '\r\n\0'
else:
    print("pipe-test.py, running on linux or mac")
    TONAME = '/tmp/audacity_script_pipe.to.' + str(os.getuid())
    FROMNAME = '/tmp/audacity_script_pipe.from.' + str(os.getuid())
    EOL = '\n'

if not os.path.exists(TONAME):
    print(" ..does not exist.  Ensure Audacity is running with mod-script-pipe.")
    sys.exit()

if not os.path.exists(FROMNAME):
    print(" ..does not exist.  Ensure Audacity is running with mod-script-pipe.")
    sys.exit()
print("-- Both pipes exist.  Good.")
TOFILE = open(TONAME, 'w')
print("-- File to write to has been opened")
FROMFILE = open(FROMNAME, 'rt')
print("-- File to read from has now been opened too\r\n")

'''
Audacity Functions
'''
# Send a single command to audacity mod-script-pipeline
def send_command(command):
    #print("Send: >>> \n"+command)
    TOFILE.write(command + EOL)
    TOFILE.flush()

# Return the command response
def get_response():
    result = ''
    line = ''
    while line != '\n':
        result += line
        line = FROMFILE.readline()
    return result

# Send one command, and return the response
def do_command(command):
    send_command(command)
    response = get_response()
    #print("Rcvd: <<< \n" + response)
    return response

'''
Utility Functions
'''
# Remove any chars from string that are not english characters or numbers
def slugify(value):
    valStr = re.sub('[^A-Za-z0-9()]+', ' ', value)
    return valStr

# Format output filepath
def formatOutputFilepath(outputLocation, outputFormat, filename):
    #create final output filepath with filename and extension (audacity needs this)
    if sys.platform == 'win32':
        #if outputLocation folder doesn't exist, create it
        if not os.path.exists(outputLocation):
            os.makedirs(outputLocation)
            print('directory created')

        outputFileLocation = outputLocation + '\\' + filename + "." + outputFormat 
    else:
        print('mac/linux option outputfile')
        #if outputLocation folder doesn't exist, create it
        if not os.path.exists(outputLocation):
            os.makedirs(outputLocation)
            print('directory created')
        outputFileLocation = outputLocation + '' + title + "." + outputFormat 
    outputFileLocation = os.path.abspath(outputFileLocation)
    return outputFileLocation

# Export tracks from Audacity
def renderAudacityTracks(metadataInput, outputLocation, outputFormat):
    # If 'tracks' key exists in metadataInput
    if 'tracks' in metadataInput:
        #render each track in tracks
        for i in range(0, len(metadataInput["tracks"])):
            print("Exporting track ", i+1, "out of", len(metadataInput["tracks"]))
            title = metadataInput["tracks"][i]
            #go to next clip for selection
            do_command('SelNextClip')
            # Set filename
            filename = str(i+1) + '. ' + title
            # Create full output filepath
            outputFileLocation = formatOutputFilepath(outputLocation, outputFormat, filename) 
            print("Location: "+str(outputFileLocation))
            #print("Rendering file to ", outputFileLocation)
            renderCommand = 'Export2: Mode=Selection Filename="' + outputFileLocation + '" NumChannels=2 '
            cmdResult = do_command(renderCommand)
            time.sleep(5) # Delay for 5 seconds.
            print("Finished exporting track\n")

# Input Full Discogs URL, output Metadata Tags
def getDiscogsTags(discogsURL):
    metadataTags = {}
    discogsURL=discogsURL.strip()
    #get ID and type from discogsURL
    discogsSplit = discogsURL.rsplit('/', 2)
    
    discogsType = discogsSplit[-2]

    discogsID = discogsSplit[2]
    if "-" in discogsID:
        discogsIDSplit = discogsID.split('-')
        discogsID=discogsIDSplit[0]
    

    #make discogs api call
    requestURL = 'https://api.discogs.com/' + discogsType + 's/' + discogsID

    response = requests.get(requestURL)
    discogsAPIResponse_status_code = response.status_code
    if discogsAPIResponse_status_code == 200:
        print(requestURL)
        print("Discogs API Status Code = 200")
        #get artist name string
        jsonData = json.loads(response.text)
        #get artist(s) name as string
        artistString = ""
        artistNum = 0
        if 'artists' in jsonData:
            for artist in jsonData['artists']:
                if artistNum == 0:
                    artistString = artist['name']
                else:
                    artistString = artistString + ', ' + artist['name']
                    artistNum = artistNum + 1
        #remove any int between parenthesis
        artistString = re.sub(r'\(([\d)]+)\)', '', artistString)

        #get tracklist
        tracks = []
        tracklist = jsonData['tracklist']
        trackNum = 1
        for track in tracklist:
            if track['type_'] == 'track':
                trackTitle = track['title']
                #sanitize tracktitle
                trackTitle = slugify(trackTitle)
                tracks.append(trackTitle)
                trackNum = trackNum + 1
        
        #get album title
        albumTitle = getValueIfExists(jsonData, 'title')

        #get releaseDate
        releaseDate = getValueIfExists(jsonData, 'released')

    else:
        print("ERROR: Discogs API request did not complete.")
    metadataTags = {'album':albumTitle, 'artist':artistString, 'year':releaseDate, 'tracks':tracks }   
    return metadataTags

def getValueIfExists(dataObj, keyStr):
    defualtVal = ''
    if keyStr in dataObj:
        defualtVal = dataObj[keyStr]
    return defualtVal

def getManualTags():
    return 'wip'

'''
#############################################
Start processing command line args 
#############################################
'''
print('~ vinyl2digital ~')

# -h 
# Print help information
if '-h' in sys.argv:
    print('Welcome to the vinyl2digital pip package: v1.0.3')
    
    print('-t')
    print('Test audacity pipe "Help" commands')

    print('-h')
    print('View the help page')
    
    print('-i discogs https://www.discogs.com/master/14720-Pink-Floyd-Obscured-By-Clouds')
    print('Take discogs url as input')

    print('-i 12')
    print('Export x number of audio files with default filenames, in this case 12 audio files would be exported.')

    print('-f flac')
    print('Set output audio file format (flac, mp3, etc...)')


    print('-o "E:\outputFolder"')
    print('Set output folder location')
    print('\nEnd of help output\n')

# -t
# Test audacity connection
if '-t' in sys.argv:
    do_command('Help: Command=Help')
    do_command('Help: Command="GetInfo"')  

# -i
# Get input and set metadataInput{} object
metadataInput = {}
if '-i' in sys.argv:
    # get string which comes after -i
    inputIndex = sys.argv.index('-i')
    inputValueIndex = sys.argv[inputIndex+1]

    if inputValueIndex == 'discogs':
        discogsCode = inputValueIndex = sys.argv[inputIndex+2]
        metadataInput = getDiscogsTags(discogsCode)

    else:
        numberOfTracks = int(sys.argv[inputIndex+1])
        tracks=[]
        for i in range(0, numberOfTracks):
            tracks.append('filename')
        metadataInput['tracks']=tracks

# -f
# Set audio output file format (by default export flac)
outputFormat = "flac"
if '-f' in sys.argv:
    outputFormatIndex = sys.argv.index('-f')
    outputFormat = sys.argv[outputFormatIndex+1]

# -o
# Set audio output filepath location
outputFilepath = ""
if '-o' in sys.argv:
    outputFilepathIndex = sys.argv.index('-o')
    outputFilepath = sys.argv[outputFilepathIndex+1]

if outputFilepath != "" and metadataInput != {}:
    # Begin exporting Audacity tracks
    renderAudacityTracks(metadataInput, outputFilepath, outputFormat)
else:
    print("Please specify an input ( -i ) and output ( -o )")

