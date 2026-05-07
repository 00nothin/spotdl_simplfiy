spotdl_simplify
A streamlined Linux command-line tool designed to convert Spotify links into a clean, organized, and tagged offline music library. By combining Spotify's structural data with YouTube's audio library, it automates the process of downloading, tagging, and enriching your music collection.

spotdl_simplify
A streamlined Linux command-line tool designed to convert Spotify links into a clean, organized, and tagged offline music library. By combining Spotify's structural data with YouTube's audio library, it automates the process of downloading, tagging, and enriching your music collection.

Key Functionalities
The utility is divided into two primary workflows to ensure your library is consistent and high-quality.

1. Music Downloader
Source Extraction: Scrapes Spotify playlist or album data via the web embed player.

Intelligent Search: Uses yt-dlp to find the best audio match on YouTube.

Format Conversion: Automatically converts audio to high-quality MP3 (0-quality VBR).

Initial Tagging: Applies basic metadata immediately after the download finishes.

2. Metadata Enrichment ("Fix Mode")
If you have existing files or just finished a download, this mode performs a "scorched-earth" metadata update:

Multi-Source Lookup: Aggregates data from Spotify, iTunes, and MusicBrainz.

High-Res Artwork: Fetches and embeds high-quality album covers.

Lyrics Integration: Automatically downloads both plain text and synced (LRC) lyrics from lrclib and lyrics.ovh.

Standardization: Rewrites ID3 tags (v2.3) to ensure compatibility across all media players.

Installation
System Dependencies
You must have yt-dlp and ffmpeg installed on your system.

Arch Linux:
 sudo pacman -S yt-dlp ffmpeg

Debian/Ubuntu:
 sudo apt install yt-dlp ffmpeg

 Python Setup
Clone the repository and run the script. The script will automatically check for and install required Python libraries (requests, mutagen, rich).

git clone https://github.com/00nothin/spotdl_simplfiy
cd spotdl_simplfiy
python music.py
Usage
Interactive Menu
Simply run the script without arguments to access the user interface:

python music.py
Command Line Arguments
For automation or quick actions, you can pass commands directly:

Download a playlist or album:

python music.py download <spotify_url> <destination_folder>
Fix metadata in a specific folder:

python music.py fix ~/Music/NewImports
Preview changes (Dry Run):

python music.py fix ~/Music/NewImports --dry
