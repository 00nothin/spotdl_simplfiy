# 🎵 Music Tool

A Linux CLI tool to download Spotify playlists/albums as MP3s with full metadata — album art, synced lyrics, and tags — all from the terminal.

---

## Features

- **Download** — Paste a Spotify playlist or album URL and get MP3s via YouTube
- **Fix Tags** — Scorched-earth metadata rewrite: Spotify art, synced lyrics, and all ID3 tags
- **Auto metadata** — Pulls from Spotify → iTunes → MusicBrainz (fallback chain)
- **Synced lyrics** — Embeds timed lyrics (SYLT) + plain lyrics (USLT)
- **Interactive menu** or direct CLI commands
- **Auto-installs** Python dependencies on first run

---

## Requirements

### System packages

Install these before running:

**Arch:**
```bash
sudo pacman -S yt-dlp ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt install yt-dlp ffmpeg
```

**Fedora:**
```bash
sudo dnf install yt-dlp ffmpeg
```

### Python

Python 3.8+ is required. The script auto-installs Python packages on first run:

- `requests`
- `mutagen`
- `rich`

Or install them manually:

```bash
pip install -r requirements.txt
```

---

## Installation

```bash
git clone https://github.com/YOUR_USERNAME/music-tool.git
cd music-tool
```

No further setup needed — just run it.

---

## Usage

### Interactive menu

```bash
python music.py
```

### Download a Spotify playlist or album

```bash
python music.py download <spotify_url>
```

### Fix metadata on an existing MP3 folder

```bash
python music.py fix ~/Music
python music.py fix ~/Music --dry   # preview without changes
```

---

## How It Works

1. Parses your Spotify playlist/album URL to get track list
2. Searches YouTube for each track and downloads via `yt-dlp`
3. Converts to MP3 with `ffmpeg`
4. Looks up metadata from Spotify → iTunes → MusicBrainz
5. Embeds cover art, synced lyrics, and all ID3 tags via `mutagen`

---

## Notes

- Requires an active internet connection
- Uses Spotify's anonymous web token (no API key needed)
- Crash logs are saved to `~/music_tool_crash.log`

---

## License

MIT
