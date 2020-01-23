# commandLineMusicVideo

This is a Python3 [pip package](https://pypi.org/project/vinyl2digital) that connencts to Audacity's [mod-script-pipe for Python scripting](https://manual.audacityteam.org/man/scripting.html).  

This package will batch render each selection of an Audacity track to mp3 files with metadata tags based on a Discogs URL. vinyl2digital makes digitizing vinyl records much easier and faster. 

## Quickstart
* Install the package with this command: ```pip install vinyl2digital==0.0.3```
* Launch Audacity from your terminal (Windows 10: ```start audacity.exe```)
* Record your audio, and splice each song as its own selection on the track (place the cursor and press Ctrl+i)
![step1](https://i.imgur.com/s7ktUmZ.png)
* Run the installed package with ```python3 -m vinyl2digital -h -t``` to view the help page and test your package's connecting to Audacity.
* While Audacity is open, run the pip package from the command line.

## Audacity Connection
Follow the step's listed on [this](https://manual.audacityteam.org/man/scripting.html#Enable_mod-script-pipe) page: Go to "Audacity -> Edit -> Preferences -> Modules" and set the "mod-script-pipe" parameter to "Enabled", restart Audacity and confirm that "mod-script-pipe" is set to "Enabled" by default.

## Example commands:
```python3 -m vinyl2digital -discogs 1525832 -img front.jpg "..\..\..\..\martinradio\uploads\my output folder"```
This command:
* Will get the metadata from the [Discogs release page with id=1525832](https://www.discogs.com/Anthony-And-The-Camp-Suspense/release/1525832) 
* Will tag the output mp3 files with albumart from the location: ```..\..\..\..\martinradio\uploads\my output folder\front.jpg```
* Will render each selection from the open Audacity program as an individual mp3 file in order from left to right, with tags for title, album name, artist, year, track number, and title. The files will be rendered to ```..\..\..\..\martinradio\uploads\my output folder```

## Flags

```-t``` Test audacity pipe "Help" commands.

```--h``` View the help page

```--discogs 2342323``` Discogs release ID from URL to base tags off of.

```--img front.jpg``` (optional) Filename of image located inside your output folder to use as albumart for mp3 files.

```-h``` Display help.
   
