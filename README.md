<h1>Vinyl2Digital - PyPi Package</h1>
==================================

**[Vinyl2Digital](https://pypi.org/project/vinyl2digital/) is a Python3 Pip Package for batch rendering multiple audio files using the [Audacity](https://www.audacityteam.org/download/) mod-script-pipe.**

Install with `pip install vinyl2digital`

Update with `pip install --upgrade vinyl2digital`


[![PyPi version](https://badgen.net/pypi/v/vinyl2digital/)](https://pypi.org/project/vinyl2digital) ![PyPI - Downloads](https://img.shields.io/pypi/dm/vinyl2digital) ![PyPI - License](https://img.shields.io/pypi/l/vinyl2digital) ![PyPI - Python Version](https://img.shields.io/pypi/pyversions/vinyl2digital)

<img src="readme-gif-1.gif" alt="Demonstration gif" width="950"/>


## Table of content

- [Installation](#installation)
- [Setup](#setup)
- [All Flags](#flags)
- [Example Use Cases](#examples)
- [Development](#development)

## Installation
* Install the package with this command: 
```
pip install vinyl2digital
``` 

## Setup
* Enable mod-script-pipe in Audacity

<img src="readme-img-1.png" alt="Enable mod-script-pipe" width="700"/>

* Launch Audacity from your terminal
    - Windows Command Prompt Admin
        - Navigate to Audacity executable location `cd C:\Program Files\Audacity>`
        - Launch Audacity: ```start audacity.exe```
    - Mac/Linux: ```open -a Audacity```
* Record your audio and splice each track into its own selection (place cursor and press Ctrl+i)
<img src="readme-img-2.png" alt="Split Audio Track" width="700"/>
* Highlight any selected region and choose File->Export->Export Selected Audio, these quality options will be what vinyl2digital uses. So if you want 24 bit FLAC files make sure that option is set in this window. 
<img src="readme-img-3.png" alt="Split Audio Track" width="700"/>
* Move your cursor to be at the start of your recording
* While Audacity is open, run the vinyl2digital python package with the `-t` flag to test your connection to the Audacity mod-script-pipe.

```
python -m vinyl2digital -t
```

* You should now be able to use the vinyl2digital package from the command line to connect with Audacity and batch render multiple audio files one after the other.
# Flags

## Help
* ```-h``` 
    - View the help page
* ```-t``` 
    - Test your connection to the Audacity mod-script-pipe

## Input
* ```-i discogs https://www.discogs.com/master/14720``` 
    - Take a Discogs URL as input for determining how may audio files to export and what metadata to use
* ```-i 12``` 
    - Export 12 tracks using default filenames

## Output Audio Format
* ```-f flac```
    - Export selections as flac audio files
* ```-f mp3```
    - Export selections as mp3 audio files

## Output
* ```-o "E:\martinradio\rips\vinyl\NewEnglandTeenScene"```
    - Set filepath output location
    



## Examples
* Here are some example commands for vinyl2digital on Win10 command prompt:
* ## Export tracks as flac using a Discogs URL
```
python -m vinyl2digital -i discogs https://www.discogs.com/release/2019460-Various-The-New-England-Teen-Scene -f flac -o "E:\martinradio\rips\vinyl\NewEnglandTeenScene" 
```
* ## Export 5 tracks as mp3 using default filenames
```
python -m vinyl2digital -i 5 -f mp3 -o "E:\martinradio\rips\vinyl\NewEnglandTeenScene" 
```
## Development
* In order to develop and test this code locally clone this github repo:

```git clone https://github.com/MartinBarker/vinyl2digital.git```

* Install the necessary packages: `os, sys, requests, json, time, re`
* Run locally: `python3 "vinyl2digital/vinyl2digital/__init__.py" -h`

## Releasing a new version:
* Chance package version number (`setup.py`)
```
$ python -m pip install --upgrade build
$ python -m build
```
* This will create the dist/ folder with a new packaged tar
```
python3 setup.py sdist bdist_wheel
pip3 install twine
python3 -m twine upload dist/*
```
