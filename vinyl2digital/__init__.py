#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Vinyl2Digital - A Python package for batch rendering audio files using Audacity mod-script-pipe.

This module provides functionality to export multiple audio tracks from Audacity
with metadata support from Discogs or manual track counting.
"""

import os
import sys
import requests
import json
import time
import re
import logging
from typing import Dict, List, Optional, Union
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Constants
SUPPORTED_FORMATS = {'flac', 'mp3', 'wav', 'aiff', 'ogg'}
DEFAULT_FORMAT = 'flac'
DEFAULT_DELAY = 5  # seconds between exports

class AudacityPipeError(Exception):
    """Custom exception for Audacity pipe-related errors."""
    pass

class DiscogsAPIError(Exception):
    """Custom exception for Discogs API-related errors."""
    pass

class Vinyl2DigitalError(Exception):
    """Base exception for Vinyl2Digital errors."""
    pass

class AudacityPipe:
    """Handles communication with Audacity via mod-script-pipe."""
    
    def __init__(self):
        self.to_file = None
        self.from_file = None
        self.eol = self._get_eol()
        self.to_name, self.from_name = self._get_pipe_names()
        
    def _get_eol(self) -> str:
        """Get end-of-line character based on platform."""
        return '\r\n\0' if sys.platform == 'win32' else '\n'
    
    def _get_pipe_names(self) -> tuple:
        """Get pipe names based on platform."""
        if sys.platform == 'win32':
            return ('\\\\.\\pipe\\ToSrvPipe', '\\\\.\\pipe\\FromSrvPipe')
        else:
            uid = os.getuid()
            return (f'/tmp/audacity_script_pipe.to.{uid}', f'/tmp/audacity_script_pipe.from.{uid}')
    
    def connect(self) -> None:
        """Establish connection to Audacity pipes."""
        try:
            # Check if pipes exist
            if not os.path.exists(self.to_name):
                raise AudacityPipeError(f"Write pipe '{self.to_name}' does not exist. Ensure Audacity is running with mod-script-pipe enabled.")
            
            if not os.path.exists(self.from_name):
                raise AudacityPipeError(f"Read pipe '{self.from_name}' does not exist. Ensure Audacity is running with mod-script-pipe enabled.")
            
            # Open pipes
            self.to_file = open(self.to_name, 'w')
            self.from_file = open(self.from_name, 'r')
            
            logger.info("Successfully connected to Audacity pipes")
            logger.info(f"Write pipe: {self.to_name}")
            logger.info(f"Read pipe: {self.from_name}")
            
        except Exception as e:
            raise AudacityPipeError(f"Failed to connect to Audacity pipes: {e}")
    
    def disconnect(self) -> None:
        """Close pipe connections."""
        try:
            if self.to_file:
                self.to_file.close()
            if self.from_file:
                self.from_file.close()
            logger.info("Disconnected from Audacity pipes")
        except Exception as e:
            logger.warning(f"Error during disconnect: {e}")
    
    def send_command(self, command: str) -> None:
        """Send a command to Audacity."""
        if not self.to_file:
            raise AudacityPipeError("Not connected to Audacity")
        
        try:
            self.to_file.write(command + self.eol)
            self.to_file.flush()
            logger.debug(f"Sent command: {command}")
        except Exception as e:
            raise AudacityPipeError(f"Failed to send command '{command}': {e}")
    
    def get_response(self) -> str:
        """Get response from Audacity."""
        if not self.from_file:
            raise AudacityPipeError("Not connected to Audacity")
        
        try:
            result = ''
            line = ''
            while line != '\n':
                result += line
                line = self.from_file.readline()
            logger.debug(f"Received response: {result.strip()}")
            return result
        except Exception as e:
            raise AudacityPipeError(f"Failed to get response: {e}")
    
    def do_command(self, command: str) -> str:
        """Send a command and return the response."""
        self.send_command(command)
        return self.get_response()
    
    def test_connection(self) -> bool:
        """Test the connection by sending help commands."""
        try:
            logger.info("Testing Audacity connection...")
            self.do_command('Help: Command=Help')
            self.do_command('Help: Command="GetInfo"')
            logger.info("✓ Audacity connection test successful")
            return True
        except Exception as e:
            logger.error(f"✗ Audacity connection test failed: {e}")
            return False

class FileExporter:
    """Handles file export operations."""
    
    @staticmethod
    def slugify(value: str) -> str:
        """Remove non-alphanumeric characters from string."""
        return re.sub(r'[^A-Za-z0-9()]+', ' ', value)
    
    @staticmethod
    def format_output_filepath(output_location: str, output_format: str, filename: str) -> Path:
        """Format and validate output filepath."""
        try:
            output_path = Path(output_location)
            
            # Create directory if it doesn't exist
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Create full filepath
            output_file = output_path / f"{filename}.{output_format}"
            
            # Convert to absolute path and normalize
            output_file = output_file.resolve()
            
            logger.info(f"Output file: {output_file}")
            logger.debug(f"Directory exists: {output_file.parent.exists()}")
            
            return output_file
            
        except Exception as e:
            raise Vinyl2DigitalError(f"Failed to format output filepath: {e}")
    
    @staticmethod
    def verify_file_creation(file_path: Path) -> bool:
        """Verify that a file was created successfully."""
        if file_path.exists():
            file_size = file_path.stat().st_size
            logger.info(f"✓ File created successfully: {file_path}")
            logger.info(f"  Size: {file_size} bytes")
            return True
        else:
            logger.error(f"✗ File was not created: {file_path}")
            return False

class DiscogsAPI:
    """Handles Discogs API interactions."""
    
    BASE_URL = "https://api.discogs.com"
    
    @staticmethod
    def get_metadata(discogs_url: str) -> Dict[str, Union[str, List[str]]]:
        """Fetch metadata from Discogs API."""
        try:
            # Parse URL to extract type and ID
            url_parts = discogs_url.strip().rsplit('/', 2)
            if len(url_parts) < 3:
                raise DiscogsAPIError("Invalid Discogs URL format")
            
            discogs_type = url_parts[-2]
            discogs_id = url_parts[2].split('-')[0]  # Remove any suffix after ID
            
            # Construct API URL
            api_url = f"{DiscogsAPI.BASE_URL}/{discogs_type}s/{discogs_id}"
            logger.info(f"Fetching metadata from: {api_url}")
            
            # Make API request
            response = requests.get(api_url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract metadata
            metadata = {
                'album': DiscogsAPI._get_value(data, 'title'),
                'artist': DiscogsAPI._extract_artists(data),
                'year': DiscogsAPI._get_value(data, 'year'),
                'tracks': DiscogsAPI._extract_tracks(data)
            }
            
            logger.info(f"Successfully fetched metadata for: {metadata['album']}")
            return metadata
            
        except requests.RequestException as e:
            raise DiscogsAPIError(f"Discogs API request failed: {e}")
        except json.JSONDecodeError as e:
            raise DiscogsAPIError(f"Invalid JSON response from Discogs: {e}")
        except Exception as e:
            raise DiscogsAPIError(f"Unexpected error fetching Discogs metadata: {e}")
    
    @staticmethod
    def _get_value(data: Dict, key: str, default: str = '') -> str:
        """Safely get value from dictionary."""
        return str(data.get(key, default))
    
    @staticmethod
    def _extract_artists(data: Dict) -> str:
        """Extract artist names from Discogs data."""
        artists = []
        if 'artists' in data:
            for artist in data['artists']:
                name = artist.get('name', '')
                # Remove year in parentheses
                name = re.sub(r'\(\d+\)', '', name).strip()
                if name:
                    artists.append(name)
        
        return ', '.join(artists) if artists else 'Unknown Artist'
    
    @staticmethod
    def _extract_tracks(data: Dict) -> List[str]:
        """Extract track list from Discogs data."""
        tracks = []
        tracklist = data.get('tracklist', [])
        
        for track in tracklist:
            if track.get('type_') == 'track':
                title = track.get('title', '')
                if title:
                    # Sanitize track title
                    sanitized_title = FileExporter.slugify(title).strip()
                    if sanitized_title:
                        tracks.append(sanitized_title)
        
        return tracks

class TrackRenderer:
    """Handles rendering of audio tracks."""
    
    def __init__(self, pipe: AudacityPipe):
        self.pipe = pipe
    
    def render_tracks(self, metadata: Dict, output_location: str, output_format: str) -> None:
        """Render all tracks from metadata."""
        try:
            tracks = metadata.get('tracks', [])
            if not tracks:
                raise Vinyl2DigitalError("No tracks found in metadata")
            
            logger.info(f"Starting export of {len(tracks)} tracks")
            
            # Go to start of timeline
            self.pipe.do_command("Select: Start=0")
            
            for i, title in enumerate(tracks, 1):
                logger.info(f"Exporting track {i}/{len(tracks)}: {title}")
                
                try:
                    # Select next clip
                    self.pipe.do_command('SelNextClip')
                    
                    # Format filename
                    filename = f"{i:02d}. {title}"
                    
                    # Create output filepath
                    output_file = FileExporter.format_output_filepath(
                        output_location, output_format, filename
                    )
                    
                    # Render track
                    render_cmd = f'Export2: Mode=Selection Filename="{output_file}" NumChannels=2'
                    self.pipe.do_command(render_cmd)
                    
                    # Wait for export to complete
                    time.sleep(DEFAULT_DELAY)
                    
                    # Verify file creation
                    if not FileExporter.verify_file_creation(output_file):
                        logger.warning(f"Track {i} may not have exported correctly")
                    
                    logger.info(f"Completed track {i}/{len(tracks)}")
                    
                except Exception as e:
                    logger.error(f"Failed to export track {i}: {e}")
                    continue
            
            logger.info("Track export completed")
            
        except Exception as e:
            raise Vinyl2DigitalError(f"Failed to render tracks: {e}")

class Vinyl2Digital:
    """Main class for Vinyl2Digital operations."""
    
    def __init__(self):
        self.pipe = AudacityPipe()
        self.renderer = None
    
    def __enter__(self):
        """Context manager entry."""
        self.pipe.connect()
        self.renderer = TrackRenderer(self.pipe)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.pipe.disconnect()
    
    def test_connection(self) -> bool:
        """Test Audacity connection."""
        try:
            with self:
                return self.pipe.test_connection()
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def export_tracks(self, input_source: Union[str, int], output_location: str, 
                     output_format: str = DEFAULT_FORMAT) -> None:
        """Export tracks based on input source."""
        try:
            # Validate output format
            if output_format not in SUPPORTED_FORMATS:
                raise Vinyl2DigitalError(f"Unsupported format: {output_format}. Supported: {', '.join(SUPPORTED_FORMATS)}")
            
            # Get metadata
            if isinstance(input_source, str) and input_source.startswith('http'):
                metadata = DiscogsAPI.get_metadata(input_source)
            elif isinstance(input_source, int):
                metadata = {'tracks': [f'Track {i+1:02d}' for i in range(input_source)]}
            else:
                raise Vinyl2DigitalError(f"Invalid input source: {input_source}")
            
            # Validate output location
            output_path = Path(output_location)
            if not output_path.parent.exists():
                output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Export tracks
            with self:
                self.renderer.render_tracks(metadata, output_location, output_format)
                
        except Exception as e:
            logger.error(f"Export failed: {e}")
            raise

def print_help():
    """Print help information."""
    help_text = """
Vinyl2Digital v1.0.6 - Batch audio export from Audacity

USAGE:
    python -m vinyl2digital [OPTIONS]

OPTIONS:
    -h, --help              Show this help message
    -t, --test             Test Audacity connection
    -l, --launch           Launch Audacity (auto-detects OS)
    -i, --input SOURCE     Input source (Discogs URL or track count)
    -f, --format FORMAT    Output format (flac, mp3, wav, aiff, ogg)
    -o, --output PATH      Output directory path

EXAMPLES:
    # Test connection
    python -m vinyl2digital -t
    
    # Launch Audacity
    python -m vinyl2digital -l
    
    # Export with Discogs metadata
    python -m vinyl2digital -i "https://www.discogs.com/release/12345" -f flac -o "/path/to/output"
    
    # Export 12 tracks with default names
    python -m vinyl2digital -i 12 -f mp3 -o "/path/to/output"
    
    # Get help
    python -m vinyl2digital -h

SUPPORTED FORMATS:
    flac, mp3, wav, aiff, ogg

REQUIREMENTS:
    - Audacity running with mod-script-pipe enabled
    - Active audio project with track selections
"""
    print(help_text)

def launch_audacity():
    """Launch Audacity based on the current operating system."""
    import subprocess
    import platform
    
    system = platform.system().lower()
    
    try:
        if system == "windows":
            # Windows - try common installation paths
            audacity_paths = [
                r"C:\Program Files\Audacity\audacity.exe",
                r"C:\Program Files (x86)\Audacity\audacity.exe",
                r"C:\Users\{}\AppData\Local\Programs\Audacity\audacity.exe".format(os.getenv('USERNAME', '')),
                r"C:\Users\{}\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Audacity\Audacity.lnk".format(os.getenv('USERNAME', ''))
            ]
            
            for path in audacity_paths:
                if os.path.exists(path):
                    logger.info(f"Launching Audacity from: {path}")
                    subprocess.Popen([path], shell=True)
                    return True
            
            # If not found in common paths, try to launch from PATH
            logger.info("Audacity not found in common paths, trying to launch from PATH...")
            subprocess.Popen(["audacity"], shell=True)
            return True
            
        elif system == "darwin":  # macOS
            logger.info("Launching Audacity on macOS...")
            subprocess.run(["open", "-a", "Audacity"], check=True)
            return True
            
        elif system == "linux":
            logger.info("Launching Audacity on Linux...")
            subprocess.run(["audacity"], check=True)
            return True
            
        else:
            logger.error(f"Unsupported operating system: {system}")
            return False
            
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to launch Audacity: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error launching Audacity: {e}")
        return False

def main():
    """Main CLI entry point."""
    try:
        logger.info("~ vinyl2digital ~")
        
        # Parse command line arguments
        args = sys.argv[1:]
        
        # Handle help
        if not args or '-h' in args or '--help' in args:
            print_help()
            return
        
        # Handle test
        if '-t' in args or '--test' in args:
            vinyl = Vinyl2Digital()
            success = vinyl.test_connection()
            sys.exit(0 if success else 1)
        
        # Handle launch
        if '-l' in args or '--launch' in args:
            success = launch_audacity()
            sys.exit(0 if success else 1)
        
        # Parse required arguments
        input_source = None
        output_location = None
        output_format = DEFAULT_FORMAT
        
        # Parse input
        if '-i' in args:
            input_index = args.index('-i')
            if input_index + 1 >= len(args):
                raise Vinyl2DigitalError("Missing input value after -i")
            
            input_value = args[input_index + 1]
            
            # Check if it's a Discogs URL
            if input_value == 'discogs':
                if input_index + 2 >= len(args):
                    raise Vinyl2DigitalError("Missing Discogs URL after 'discogs'")
                input_source = args[input_index + 2]
            else:
                # Try to parse as track count
                try:
                    input_source = int(input_value)
                    if input_source <= 0:
                        raise Vinyl2DigitalError("Track count must be positive")
                except ValueError:
                    raise Vinyl2DigitalError(f"Invalid track count: {input_value}")
        
        # Parse format
        if '-f' in args:
            format_index = args.index('-f')
            if format_index + 1 >= len(args):
                raise Vinyl2DigitalError("Missing format value after -f")
            output_format = args[format_index + 1]
        
        # Parse output
        if '-o' in args:
            output_index = args.index('-o')
            if output_index + 1 >= len(args):
                raise Vinyl2DigitalError("Missing output path after -o")
            output_location = args[output_index + 1].strip('"\'')
        
        # Validate required arguments
        if input_source is None:
            raise Vinyl2DigitalError("Input source (-i) is required")
        if output_location is None:
            raise Vinyl2DigitalError("Output location (-o) is required")
        
        # Export tracks
        vinyl = Vinyl2Digital()
        vinyl.export_tracks(input_source, output_location, output_format)
        
        logger.info("Export completed successfully!")
        
    except Vinyl2DigitalError as e:
        logger.error(f"Error: {e}")
        print(f"\nError: {e}")
        print("Use -h for help")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        print("\nOperation cancelled")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"\nUnexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

