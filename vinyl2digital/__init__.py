import os
import sys
import requests
import json
import mutagen
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, APIC, ID3NoHeaderError
from mutagen.mp3 import MP3 
from mutagen.flac import FLAC
import time

import re

def slugify(value):
    """
    Remove any chars from string that arent english characters or numbers
    I intend on fixing this in the future
    """
    valStr = re.sub('[^A-Za-z0-9()]+', ' ', value)
    return valStr

#startup audacity pipe commands
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

print("Write to  \"" + TONAME +"\"")
if not os.path.exists(TONAME):
    print(" ..does not exist.  Ensure Audacity is running with mod-script-pipe.")
    sys.exit()

print("Read from \"" + FROMNAME +"\"")
if not os.path.exists(FROMNAME):
    print(" ..does not exist.  Ensure Audacity is running with mod-script-pipe.")
    sys.exit()

print("-- Both pipes exist.  Good.")

TOFILE = open(TONAME, 'w')
print("-- File to write to has been opened")
FROMFILE = open(FROMNAME, 'rt')
print("-- File to read from has now been opened too\r\n")

def send_command(command):
    """Send a single command."""
    print("Send: >>> \n"+command)
    TOFILE.write(command + EOL)
    TOFILE.flush()

def get_response():
    """Return the command response."""
    result = ''
    line = ''
    while line != '\n':
        result += line
        line = FROMFILE.readline()
    #print(" I read line:["+line+"]")
    return result

def do_command(command):
    """Send one command, and return the response."""
    send_command(command)
    response = get_response()
    print("Rcvd: <<< \n" + response)
    return response

def renderAudacityTracks(metadataInput, outputLocation, outputFormat):
    print("render() len(metadataInput[tracks] = ", len(metadataInput["tracks"]))
    #render each track in tracks
    for i in range(0, len(metadataInput["tracks"])):
        print("i = ", i, ", max = ", len(metadataInput["tracks"]))
        title = metadataInput["tracks"][i]['trackTitle']
        artist = metadataInput["tracks"][i]['trackArtist']
        album = metadataInput["album"]
        year = metadataInput["year"]
        #go to next clip for selection
        do_command('SelNextClip')
        #export selection
        
        #create final output filepath with filename and extension (audacity needs this)
        if sys.platform == 'win32':
            #if outputLocation folder doesn't exist, create it
            if not os.path.exists(outputLocation):
                os.makedirs(outputLocation)
                print('directory created')

            outputFileLocation = outputLocation + '\\' + str(i+1) + '. ' + title + "." + outputFormat 
        else:
            print('mac/linux option outputfile')
            #if outputLocation folder doesn't exist, create it
            if not os.path.exists(outputLocation):
                os.makedirs(outputLocation)
                print('directory created')
            outputFileLocation = outputLocation + '' + title + "." + outputFormat 
        
        outputFileLocation = os.path.abspath(outputFileLocation)
        #print("Rendering file to ", outputFileLocation)
        renderCommand = 'Export2: Mode=Selection Filename="' + outputFileLocation + '" NumChannels=2 '
        cmdResult = do_command(renderCommand)
        print("cmdResult = ", cmdResult)
        time.sleep(5) # Delay for 5 seconds.
        
        #file should be rendered, so now begin tagging process
        if outputFormat == 'flac':
            #wait until file has been completely rendered before tagging
            fileTagged = None 
            while fileTagged is None:
                try:
                    audio = FLAC(outputFileLocation)
                    fileTagged = True
                except:
                    pass
            #title
            audio["title"] = title
            #album
            audio['album'] = album
            #artist
            audio['artist'] = artist
            #year
            audio['date'] = year
            #trackNumber
            audio['tracknumber'] = str(i+1)
            audio.save()
            

        elif outputFormat == 'mp3':
            print("output format == mp3")
            
            #song title
            try:
                audio['title'] = str(metadataInput["tracks"][i])
            except KeyError:
                audio['title'] = ''
            
            #release artist
            try:
                audio['artist'] = str(metadataInput["artist"])
            except KeyError:
                audio['artist'] = ''

            #release title
            try:
                audio['album'] = str(metadataInput["album"])
            except KeyError:
                audio['artist'] = ''

            #release year
            try:
                audio['date'] = str(metadataInput["year"])
            except KeyError:
                audio['date'] = ''

            #release track number
            audio['tracknumber'] = str(i)
            audio.save(outputFileLocation, v1=2)
            
            try:
                audio = EasyID3(outputFileLocation) 
            except mutagen.id3.ID3NoHeaderError:
                print('exception caught')
        
            audio = mutagen.File(outputFileLocation, easy=True)   
            
    

def getDiscogsTags(discogsURL):
    metadataTags = {}
    #get ID and type from discogsURL
    discogsSplit = discogsURL.rsplit('/', 2)
    discogsID = discogsSplit[-1]
    discogsType = discogsSplit[-2]

    #make discogs api call
    requestURL = 'https://api.discogs.com/' + discogsType + 's/' + discogsID
    print("api request URL = ")
    response = requests.get(requestURL)
    discogsAPIResponse_status_code = response.status_code
    if discogsAPIResponse_status_code == 200:
        print("discogsAPIResponse_status_code == 200")
        #get artist name string
        jsonData = json.loads(response.text)
        #get artist(s) name as string
        artistString = ""
        artistNum = 0
        for artist in jsonData['artists']:
            if artistNum == 0:
                artistString = artist['name']
            else:
                artistString = artistString + ', ' + artist['name']
                artistNum = artistNum + 1
        #remove any int between parenthesis
        artistString = re.sub(r'\(([\d)]+)\)', '', artistString)
        print("artistString = ", artistString)

        #get tracklist
        tracks = []
        tracklist = jsonData['tracklist']
        trackNum = 1
        for track in tracklist:
            if track['type_'] == 'track':
                #create trackArtist string
                trackArtist = ''
                trackArtists = track['artists']
                for artist in trackArtists:
                    trackArtist = trackArtist + artist["name"]
                trackTitle = track['title']
                #sanitize tracktitle
                trackTitle = slugify(trackTitle)
                tracks.append({'trackNum':trackNum, 'trackTitle':trackTitle, 'trackArtist':trackArtist})
                trackNum = trackNum + 1
        
        #get album title
        albumTitle = jsonData['title']
        #get releaseDate
        releaseDate = jsonData['released']
        
    metadataTags = {'album':albumTitle, 'artist':artistString, 'year':releaseDate, 'tracks':tracks }    
    return metadataTags

def getManualTags():
    metadataTags = {}

    #metadataTags = {'album':'Circean', 'artist':'Circean', 'year':'1996', 'tracks':['Limbo Land', 'Miles Away', 'Hide and Seek', 'Canvas', 'His Holographic Image', 'Action Pose', 'Paper boat race', 'Quintet and Snow', 'Unintrestable Clous', 'Sonorous', 'Faraway So Close', 'Bloody Hands'] }    
    print('Is there one artst for this release or multiple artists?')
    print("Type '1' for one artist")
    print("Type '2' for multiple artists")
    numArtists = input("")
    if numArtists == "1":
        #prompt for artist name
        artistName = input("Enter artist name: ")

    #prompt for album title
    album = input("Enter album title: ")
    
    #prompt for year
    year = input("Enter release date year: ")

    #prompt for number of tracks
    numberOfTracks = input("Number of tracks for this album: ")
    
    #get trackTitle for each track
    tracks = []
    for i in range(1, int(numberOfTracks)+1):
        trackTitle = input('Enter track (%d) title: ' % i)    
        if numArtists == "2":
            trackArtist = input("Enter track artist: ")
            tracks.append({'trackTitle':trackTitle, 'trackArtist':trackArtist})
        elif numArtists == "1":
            tracks.append({'trackTitle':trackTitle, 'trackArtist':artistName})

    #contruct metadataTags
    metadataTags = {'album':album, 'artist':artistName, 'year':year, 'tracks':tracks }

    return metadataTags


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
print('~ vinyl2digital ~')
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
flags = sys.argv
if '-h' in flags:
    print('Welcome to the vinyl2digital pip package.')
    print('\n ~ Tagging Source Flags ~ \n')
    print('-h                                //view the help page')
    print('-i discogs https://www.discogs.com/Lee-Vanderbilt-Get-Into-What-Youre-In/release/974741      //use a discogs url as input for metadata')
    print('-i manual      //use manual entry as input for metadata')
    print('-f flac       //choose output audio file format (in this case, flac)')
    #print('-img front.jpg                    //(optional) filename of image to set as albumart for mp3 file tag')
    print('-o "..\..\Documents\Folder"  //folder where the files will be exported to')

#get input metadata object {}
if '-i' in flags:
    inputIndex = flags.index('-i')
    inputValueIndex = flags[inputIndex+1]
    if inputValueIndex == 'discogs':
        discogsCode = inputValueIndex = flags[inputIndex+2]
        metadataInput = getDiscogsTags(discogsCode)

    elif inputValueIndex == 'manual':
        metadataInput = getManualTags()

#get output format
outputFormat = ""
if '-f' in flags:
    outputFormatIndex = flags.index('-f')
    outputFormat = flags[outputFormatIndex+1]

#choose output filepath
outputFilepath = ""
if '-o' in flags:
    outputFilepathIndex = flags.index('-o')
    outputFilepath = flags[outputFilepathIndex+1]
    #export Audacity tracks
    print("outputFilepath = ", outputFilepath)
    print("outputFormat = ", outputFormat)
    renderAudacityTracks(metadataInput, outputFilepath, outputFormat)