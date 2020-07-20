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

""" bin2dig functions: """
def begin_bin2dig(flags):
    print("~~ bin2dig ~~ flags = ", flags)
    
    if '-t' in flags:
        do_command(r'Export2: Mode=Selection Filename="C:\Users\marti\Documents\martinradio\uploads\zxc.flac" NumChannels=2')
        #renderAudacityTracks(metadataInput, outputLocation, outputFormat):

    #get input metadata object {}
    if '-i' in flags:
        inputIndex = flags.index('-i')
        inputValueIndex = flags[inputIndex+1]
        if inputValueIndex == 'discogs':
            discogsCode = inputValueIndex = flags[inputIndex+2]
            metadataInput = getDiscogsTags(discogsCode)

        elif inputValueIndex == 'manual':
            metadataInput = getManualTags(True)

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

def renderAudacityTracks(metadataInput, outputLocation, outputFormat):
    print("render() len(metadataInput[tracks] = ", len(metadataInput["tracks"]))
    #render each track in tracks
    for i in range(0, len(metadataInput["tracks"])):
        print("i = ", i, ", max = ", len(metadataInput["tracks"]))
        title = metadataInput["tracks"][i]
        artist = metadataInput["artist"]
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
        '''
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
            ''' 
    

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
                trackTitle = track['title']
                #sanitize tracktitle
                trackTitle = slugify(trackTitle)
                print("track ", trackNum, ", title = ", trackTitle)
                tracks.append(trackTitle)
                trackNum = trackNum + 1
        
        #get album title
        albumTitle = jsonData['title']
        #get releaseDate
        releaseDate = jsonData['released']
        
    metadataTags = {'album':albumTitle, 'artist':artistString, 'year':releaseDate, 'tracks':tracks }    
    return metadataTags

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
print('~ vinyl2digital ~')
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

""" package initialization setup: """
if '-bin2dig' or '-dig2vid' in sys.argv:
    #set default indexes
    bin2digIndex = len(sys.argv)
    bin2digFlags = []

    dig2vidIndex = len(sys.argv)
    dig2vidFlags = []

    #get flags / args for bin2dig or dig2vid
    if '-bin2dig' in sys.argv:
        print("trigger bin2dig")
        #setupAudacityPipeline()
        bin2digStartIndex = sys.argv.index('-bin2dig')
        argsSplice1 = sys.argv[bin2digStartIndex:len(sys.argv)]
        if '-dig2vid' in argsSplice1:
            dig2vidIndex = argsSplice1.index('-dig2vid')
            bin2digFlags = argsSplice1[0:dig2vidIndex]
        else:
            bin2digFlags = argsSplice1[0:len(argsSplice1)]
        #execute flags
        
        begin_bin2dig(bin2digFlags)

if '-h' in sys.argv:
    print('Welcome to the vinyl2digital pip package.')
    print('\n ~ Tagging Source Flags ~ \n')
    print('-t                                //test audacity pipe "Help" commands')
    print('-h                                //view the help page')
    print('-discogs 2342323                  //discogs release ID from URL to base tags off of')
    print('-img front.jpg                    //(optional) filename of image to set as albumart for mp3 file tag')
    print('-o "/C/full/path/to/output"  //folder where the files will be exported to')

if '-t' in sys.argv:
    #test audacity connection
    do_command('Help: Command=Help')
    do_command('Help: Command="GetInfo"')  

if '-o' in sys.argv:
    #get output filepath location
    outputLocationIndex = sys.argv.index('-o')
    outputLocation = sys.argv[outputLocationIndex+1]

if '-discogs' in sys.argv:
    #get discogs release id
    discogsReleaseIDIndex = sys.argv.index('-discogs')
    discogsReleaseID = sys.argv[discogsReleaseIDIndex+1]

    response = requests.get('https://api.discogs.com/releases/'+discogsReleaseID)
    print("response = ")
    print(response)

    print("discogs api response code = ", response.status_code)
    #print("response.text = ", response.text)

    if response.status_code == 200:
        #get titles from discogs api call
        print("successful discogs api call") 
        jsonData = json.loads(response.text)
        #get artist(s) name as string
        artistString = ""
        artistNum = 0
        for artist in jsonData['artists']:
            if artistNum == 0:
                artistString = artist['name']
            else:
                print('else')
                artistString = artistString + ', ' + artist['name']
                artistNum = artistNum + 1
        print("artistString = ", artistString)

    #skip to start of track
    do_command('Select: Start=0 End=0')
 
    #get current working dir
    os.chdir(os.path.dirname(__file__))

    #get tracklist
    tracklist = jsonData['tracklist']
    print("\n" + str(len(tracklist)) + " songs in tracklist. ")
    trackNum = 1
    #render each track
    for track in tracklist:
        #go to next clip for selection
        do_command('SelNextClip')
        #export selection
 
        #get tracktitle from discogs
        trackTitle = track['title']
        #sanitize tracktitle
        trackTitle = slugify(trackTitle)
        print("sanitized trackTitle = ", trackTitle)
        #create final output filepath with filename and extension (audacity needs this)
        if sys.platform == 'win32':
            print('outputLocation = ' + outputLocation)
            #if outputLocation folder doesn't exist, create it
            #if not os.path.exists(outputLocation):
            #    os.makedirs(outputLocation)
            #    print('directory created')

            outputFileLocation = outputLocation + '\\' + str(trackNum) + ". " + trackTitle + ".mp3"
        else:
            print('mac/linux option outputfile')
            #if outputLocation folder doesn't exist, create it
            if not os.path.exists(outputLocation):
                os.makedirs(outputLocation)
                print('directory created')
            outputFileLocation = outputLocation + '/' + str(trackNum) + ". " + trackTitle + ".mp3"
            #"/Users/martin/Documents/tempFolder/song.mp3" 
 
        print("outputFileLocation = ", outputFileLocation)

        do_command('Export2: Mode=Selection Filename="' + outputFileLocation + '" NumChannels=2 ')
 
        #if -noTags is not included:
        if '-noTags' not in sys.argv:
            print('Begin tagging process')
            try:
                audio = EasyID3(outputFileLocation) 
            except mutagen.id3.ID3NoHeaderError:
                print('exception caught')
 
            audio = mutagen.File(outputFileLocation, easy=True)    
            #song title
            try:
                audio['title'] = track['title'] 
            except KeyError:
                audio['title'] = ''
            
            #release artist
            try:
                audio['artist'] = artistString
            except KeyError:
                audio['artist'] = ''

            #release title
            try:
                audio['album'] = jsonData['title']
            except KeyError:
                audio['artist'] = ''

            #release year
            try:
                audio['date'] = jsonData['released']
            except KeyError:
                audio['date'] = ''
            #release track number
            audio['tracknumber'] = str(trackNum)
            audio.save(outputFileLocation, v1=2)

        else:
            print('do not do tags')

        trackNum = trackNum + 1
