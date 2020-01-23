import os
import sys
import requests
import json
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, APIC

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

print('~ vinyl2digital ~')
#quick_test()

if '-h' in sys.argv:
    print('Welcome to the vinyl2digital pip package.')
    print('\n ~ Tagging Source Flags ~ \n')
    print('-t                             //test audacity pipe "Help" commands')
    print('-h                             //view the help page')
    print('-discogs 2342323               //discogs release ID from URL to base tags off of')
    print('-img front.jpg                 //(optional) filename of image to set as albumart for mp3 file tag')
    print('The last argument is always the output destination filepath.')

if '-t' in sys.argv:
    #test audacity connection
    do_command('Help: Command=Help')
    do_command('Help: Command="GetInfo"')  

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
        for track in tracklist:
            #go to next clip for selection
            do_command('SelNextClip')
            #export each audacity selection
            outputLocation = sys.argv[len(sys.argv)-1]
            outputFileLocation = os.getcwd() + "\\" +  outputLocation + '\\' + str(trackNum) + ". " + track['title'] + ".mp3" 
            print("outputFileLocation = ", outputFileLocation)
            do_command('Export2: Mode=Selection Filename="' + outputFileLocation + '" NumChannels=2 ')
            trackNum = trackNum + 1

            #tag output file
            audio = EasyID3(outputFileLocation) 
            audio['title'] = track['title'] 
            audio['artist'] = artistString
            audio['album'] = jsonData['title']
            audio['date'] = jsonData['released']
            audio['tracknumber'] = str(trackNum)
            audio.save()

            if '-img' in sys.argv:
                imgNameIndex = sys.argv.index('-img')
                imgName = sys.argv[imgNameIndex+1]
                #set song albumart image
                audio = ID3(outputFileLocation)
                imgLocation = os.getcwd() + "\\" +  outputLocation + '\\' + imgName
                print('imgLocation = ', imgLocation)
                with open(imgLocation, 'rb') as albumart:
                    audio['APIC'] = APIC(
                        encoding=3,
                        mime='image/jpeg',
                        type=3, desc=u'Cover',
                        data=albumart.read()
                    )
                audio.save()

    else:
        print("unsuccessful discogs api call")
    
    