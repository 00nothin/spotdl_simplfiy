# 🎵 Music Tool

A terminal-based music utility for downloading Spotify playlists/albums as MP3s using YouTube sources, with automatic metadata fixing, album art, and synced lyrics support.

> This project is unofficial and is not affiliated with Spotify, YouTube, Apple, or MusicBrainz.

---

# Features

## Download Spotify playlists/albums

* Paste a Spotify playlist or album URL
* Tracks are matched and downloaded from YouTube using `yt-dlp`
* Automatically converted to MP3 with `ffmpeg`

## Metadata fixing

Rewrites MP3 tags with improved metadata from:

1. Spotify
2. iTunes
3. MusicBrainz

Includes:

* Title
* Artist
* Album
* Year
* Track number
* Genre
* Cover art
* Lyrics

## Synced lyrics support

Embeds:

* `SYLT` timed lyrics
* `USLT` plain lyrics

Compatible with many modern music players.

## Terminal UI

* Interactive menu mode
* Direct CLI commands
* Rich progress bars and status output

## Automatic Python dependency installation

The script automatically installs required Python packages on first run.

---

# Requirements

## System packages

Install these before running the tool.

### Arch Linux

```bash
sudo pacman -S yt-dlp ffmpeg
```

### Ubuntu / Debian

```bash
sudo apt install yt-dlp ffmpeg
```

### Fedora

```bash
sudo dnf install yt-dlp ffmpeg
```

### openSUSE

```bash
sudo zypper install yt-dlp ffmpeg
```

---

# Python Requirements

Python 3.8 or newer.

The following packages are auto-installed if missing:

* requests
* mutagen
* rich

You can also install them manually:

```bash
pip install -r requirements.txt
```

---

# Installation

```bash
git clone https://github.com/YOUR_USERNAME/music-tool.git
cd music-tool
```

Run directly:

```bash
python music.py
```

---

# Usage

## Interactive menu

```bash
python music.py
```

---

## Download a Spotify playlist or album

```bash
python music.py download <spotify_url>
```

Example:

```bash
python music.py download https://open.spotify.com/playlist/XXXXXXXX
```

---

## Fix metadata on existing MP3 files

```bash
python music.py fix ~/Music
```

Preview changes without modifying files:

```bash
python music.py fix ~/Music --dry
```

---

# How It Works

1. Reads Spotify playlist/album metadata
2. Searches YouTube for matching tracks
3. Downloads audio using `yt-dlp`
4. Converts audio to MP3 using `ffmpeg`
5. Fetches metadata from Spotify → iTunes → MusicBrainz
6. Downloads album art and lyrics
7. Embeds tags using `mutagen`

---

# Notes

* Internet connection required
* Uses Spotify's public web token system
* Metadata quality depends on available sources
* Some YouTube matches may occasionally be incorrect
* Crash logs are saved to:

```text
~/music_tool_crash.log
```

---

# Legal Notice

This project downloads audio from publicly accessible YouTube sources.

Users are responsible for complying with:

* copyright laws
* YouTube Terms of Service
* local regulations

This tool is intended for personal and educational use only.

---

# Planned Improvements

* Better YouTube matching/filtering
* Parallel downloads
* FLAC support
* Playlist resume support
* Duplicate detection
* Metadata caching
* Improved Spotify API integration

---

# License

MIT
