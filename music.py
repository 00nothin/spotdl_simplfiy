#!/usr/bin/env python3
"""
music.py -- Linux Music Tool

  1. Download  -- Spotify playlist/album via YouTube + MP3 + full metadata
  2. Fix Tags  -- Scorched-earth metadata fix (Spotify art, synced lyrics)

Usage:
    python music.py                 # interactive menu
    python music.py download <url>  # download from URL
    python music.py fix <folder>    # fix tags in folder
"""

import sys, re, os, json, time, subprocess, traceback, pathlib, platform

# -- Auto-install Python deps ----
def _pip(*pkgs):
    for p in pkgs:
        subprocess.run([sys.executable, "-m", "pip", "install", p, "-q",
                        "--break-system-packages"], check=True)

try:
    import requests
except ImportError:
    print("  Installing requests..."); _pip("requests"); import requests

try:
    from mutagen.mp3 import MP3
    from mutagen.id3 import (ID3, APIC, USLT, SYLT, TIT2, TPE1,
                              TALB, TDRC, TRCK, TCON, COMM, error as ID3Error)
except ImportError:
    print("  Installing mutagen..."); _pip("mutagen")
    from mutagen.mp3 import MP3
    from mutagen.id3 import (ID3, APIC, USLT, SYLT, TIT2, TPE1,
                              TALB, TDRC, TRCK, TCON, COMM, error as ID3Error)

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt
    from rich.progress import (Progress, BarColumn, TextColumn,
                               TimeRemainingColumn, SpinnerColumn, TaskProgressColumn)
    from rich.table import Table
except ImportError:
    print("  Installing rich..."); _pip("rich")
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt
    from rich.progress import (Progress, BarColumn, TextColumn,
                               TimeRemainingColumn, SpinnerColumn, TaskProgressColumn)
    from rich.table import Table

console = Console()

# ==============================================================================
# HELPERS
# ==============================================================================

def confirm(question, default=True):
    hint = "[Y/n]" if default else "[y/N]"
    while True:
        ans = Prompt.ask(f"[cyan]{question}[/cyan] [dim]{hint}[/dim]", default="").strip().lower()
        if ans in ("y", "yes"): return True
        if ans in ("n", "no"):  return False
        if ans == "":           return default

def _cls():
    os.system("clear")

# ==============================================================================
# SYSTEM CHECKS
# ==============================================================================

def check_system_deps():
    """Verify yt-dlp and ffmpeg are available."""
    missing = []
    if subprocess.run(["which", "yt-dlp"], capture_output=True).returncode != 0:
        missing.append("yt-dlp")
    if subprocess.run(["which", "ffmpeg"], capture_output=True).returncode != 0:
        missing.append("ffmpeg")
    return missing

def install_system_deps(missing):
    """Try to install missing system packages via package manager."""
    if not missing:
        return True
    
    console.print()
    console.print("[yellow]Missing system packages: " + ", ".join(missing) + "[/yellow]")
    console.print()
    
    # Detect distro
    if os.path.exists("/etc/arch-release"):
        console.print("[dim]Arch detected. Run:[/dim]")
        console.print(f"  [cyan]sudo pacman -S {' '.join(missing)}[/cyan]")
    elif os.path.exists("/etc/debian_version"):
        console.print("[dim]Debian/Ubuntu detected. Run:[/dim]")
        console.print(f"  [cyan]sudo apt install {' '.join(missing)}[/cyan]")
    elif os.path.exists("/etc/fedora-release"):
        console.print("[dim]Fedora detected. Run:[/dim]")
        console.print(f"  [cyan]sudo dnf install {' '.join(missing)}[/cyan]")
    elif os.path.exists("/etc/opensuse-release"):
        console.print("[dim]openSUSE detected. Run:[/dim]")
        console.print(f"  [cyan]sudo zypper install {' '.join(missing)}[/cyan]")
    else:
        console.print("[dim]Unknown distro. Install manually:[/dim]")
        for pkg in missing:
            console.print(f"  [cyan]{pkg}[/cyan]")
    console.print()
    
    if not confirm("Continue without these packages? (Downloads may fail)"):
        sys.exit(1)

# ==============================================================================
# SPOTIFY ANONYMOUS TOKEN
# ==============================================================================

_spotify_token = ""
_token_expiry  = 0.0

def get_spotify_token():
    global _spotify_token, _token_expiry
    if _spotify_token and time.time() < _token_expiry:
        return _spotify_token
    try:
        r = requests.get(
            "https://open.spotify.com/get_access_token",
            params={"reason": "transport", "productType": "web_player"},
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "App-Platform": "WebPlayer",
            },
            timeout=10,
        )
        if r.status_code == 200:
            data = r.json()
            _spotify_token = data.get("accessToken", "")
            exp = data.get("accessTokenExpirationTimestampMs", 0)
            _token_expiry  = exp / 1000 if exp else time.time() + 3600
            return _spotify_token
    except Exception:
        pass
    return ""

# ==============================================================================
# METADATA LOOKUPS  (Spotify > iTunes > MusicBrainz)
# ==============================================================================

def clean_name(text):
    text = re.sub(r'\(.*?\)|\[.*?\]', '', text)
    text = re.sub(r'(?i)official\s*(video|audio|music\s*video)|lyric\s*video|'
                  r'remastered|hd|4k|high\s*quality|full\s*audio', '', text)
    return text.strip()

def search_spotify(artist, title):
    token = get_spotify_token()
    if not token: return {}
    try:
        r = requests.get(
            "https://api.spotify.com/v1/search",
            params={"q": f"{clean_name(artist)} {clean_name(title)}",
                    "type": "track", "limit": 1},
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        if r.status_code != 200: return {}
        items = r.json().get("tracks", {}).get("items", [])
        if not items: return {}
        track  = items[0]
        album  = track.get("album", {})
        images = sorted(album.get("images", []),
                        key=lambda x: x.get("width", 0), reverse=True)
        return {
            "title":   track.get("name", ""),
            "artist":  ", ".join(a["name"] for a in track.get("artists", [])),
            "album":   album.get("name", ""),
            "year":    album.get("release_date", "")[:4],
            "track":   str(track.get("track_number", "")),
            "genre":   "",
            "art_url": images[0]["url"] if images else "",
        }
    except Exception:
        return {}

def lookup_itunes(artist, title):
    try:
        r = requests.get(
            "https://itunes.apple.com/search",
            params={"term": f"{clean_name(artist)} {clean_name(title)}",
                    "entity": "song", "limit": 1},
            timeout=10,
        )
        if r.status_code != 200: return {}
        results = r.json().get("results", [])
        if not results: return {}
        res = results[0]
        art = res.get("artworkUrl100", "").replace("100x100bb.jpg", "3000x3000bb.jpg")
        return {
            "title":   res.get("trackName", ""),
            "artist":  res.get("artistName", ""),
            "album":   res.get("collectionName", ""),
            "year":    res.get("releaseDate", "")[:4],
            "track":   str(res.get("trackNumber", "")),
            "genre":   res.get("primaryGenreName", ""),
            "art_url": art,
        }
    except Exception:
        return {}

def lookup_musicbrainz(artist, title):
    try:
        q = f'recording:"{clean_name(title)}"'
        if artist:
            q += f' AND artist:"{clean_name(artist)}"'
        r = requests.get(
            "https://musicbrainz.org/ws/2/recording",
            params={"query": q, "limit": 1, "fmt": "json"},
            headers={"User-Agent": "MusicTool/2.0 (linux)"},
            timeout=10,
        )
        if r.status_code != 200: return {}
        recs = r.json().get("recordings", [])
        if not recs: return {}
        rec      = recs[0]
        c_artist = rec.get("artist-credit", [{}])[0].get("artist", {}).get("name", "")
        releases = rec.get("releases", [])
        c_album = c_year = c_track = ""
        if releases:
            rel     = releases[0]
            c_album = rel.get("title", "")
            c_year  = rel.get("date", "")[:4]
            media   = rel.get("media", [])
            if media:
                c_track = str(media[0].get("track-offset", 0) + 1)
        return {"title": rec.get("title", ""), "artist": c_artist,
                "album": c_album, "year": c_year, "track": c_track, "genre": ""}
    except Exception:
        return {}

def best_meta(artist, title, existing):
    spotify = search_spotify(artist, title);  time.sleep(0.2)
    itunes  = lookup_itunes(artist, title)  if not spotify else {};  time.sleep(0.2)
    mb      = lookup_musicbrainz(artist, title) if not spotify else {};  time.sleep(0.2)
    def pick(*vals):
        return next((v for v in vals if v), "")
    return {
        "title":   pick(spotify.get("title"),  itunes.get("title"),  mb.get("title"),  title),
        "artist":  pick(spotify.get("artist"), itunes.get("artist"), mb.get("artist"), artist),
        "album":   pick(spotify.get("album"),  itunes.get("album"),  mb.get("album"),  existing.get("album", "")),
        "year":    pick(spotify.get("year"),   itunes.get("year"),   mb.get("year"),   existing.get("year", "")),
        "track":   pick(spotify.get("track"),  itunes.get("track"),  mb.get("track"),  existing.get("track", "")),
        "genre":   pick(spotify.get("genre"),  itunes.get("genre"),  mb.get("genre"),  "Music"),
        "art_url": pick(spotify.get("art_url"), itunes.get("art_url"), ""),
    }

# ==============================================================================
# ART + LYRICS
# ==============================================================================

def fetch_thumbnail(url):
    if not url: return None
    try:
        r = requests.get(url, timeout=15)
        if r.status_code == 200 and r.content:
            return r.content
    except Exception:
        pass
    return None

def parse_lrc(lrc):
    synced = []
    for line in lrc.splitlines():
        m = re.match(r'\[(\d+):(\d+\.\d+)\](.*)', line)
        if m:
            ms   = int((int(m.group(1)) * 60 + float(m.group(2))) * 1000)
            text = m.group(3).strip()
            if text:
                synced.append((text, ms))
    return synced

def fetch_lyrics(artist, title):
    try:
        r = requests.get(
            "https://lrclib.net/api/search",
            params={"artist_name": artist, "track_name": title},
            timeout=10,
        )
        if r.status_code == 200 and r.json():
            best        = r.json()[0]
            synced_raw  = best.get("syncedLyrics", "") or ""
            plain       = best.get("plainLyrics",  "") or ""
            synced_lines = parse_lrc(synced_raw) if synced_raw else []
            if not plain and synced_raw:
                plain = re.sub(r"\[\d+:\d+\.\d+\]", "", synced_raw).strip()
            if plain or synced_lines:
                return synced_lines, plain
    except Exception:
        pass
    try:
        r = requests.get(
            f"https://api.lyrics.ovh/v1/{requests.utils.quote(artist)}"
            f"/{requests.utils.quote(title)}",
            timeout=10,
        )
        if r.status_code == 200:
            return [], r.json().get("lyrics", "").strip()
    except Exception:
        pass
    return [], ""

# ==============================================================================
# MP3 TAG READ / WRITE
# ==============================================================================

def read_tags(filepath):
    try:
        audio = MP3(filepath, ID3=ID3)
        tags  = audio.tags or {}
        return {
            "title":  str(tags.get("TIT2", "")).strip(),
            "artist": str(tags.get("TPE1", "")).strip(),
            "album":  str(tags.get("TALB", "")).strip(),
            "track":  str(tags.get("TRCK", "")).strip(),
            "year":   str(tags.get("TDRC", "")).strip(),
        }
    except Exception:
        return {"title": "", "artist": "", "album": "", "track": "", "year": ""}

def guess_from_filename(filepath):
    name = os.path.splitext(os.path.basename(filepath))[0]
    name = clean_name(name)
    if " - " in name:
        parts = name.split(" - ", 1)
        return parts[0].strip(), parts[1].strip()
    return "", name.strip()

def write_tags(filepath, meta, cover_data, synced_lines, plain_lyrics):
    try:
        try:
            tags = ID3(filepath)
        except ID3Error:
            tags = ID3()
        tags.delete(filepath)
        if meta.get("title"):  tags.add(TIT2(encoding=3, text=meta["title"]))
        if meta.get("artist"): tags.add(TPE1(encoding=3, text=meta["artist"]))
        if meta.get("album"):  tags.add(TALB(encoding=3, text=meta["album"]))
        if meta.get("year"):   tags.add(TDRC(encoding=3, text=meta["year"]))
        if meta.get("track"):  tags.add(TRCK(encoding=3, text=meta["track"]))
        tags.add(TCON(encoding=3, text=meta.get("genre") or "Music"))
        tags.add(COMM(encoding=3, lang="eng", desc="", text="Fixed via music.py"))
        if plain_lyrics:
            tags.add(USLT(encoding=3, lang="eng", desc="", text=plain_lyrics))
        if synced_lines:
            tags.add(SYLT(encoding=3, lang="eng", format=2, type=1,
                          desc="", text=synced_lines))
        if cover_data:
            tags.add(APIC(encoding=3, mime="image/jpeg", type=3,
                          desc="Cover", data=cover_data))
        tags.save(filepath, v2_version=3)
        return True
    except Exception as e:
        console.print(f"[red]  Save failed: {e}[/red]")
        return False

# ==============================================================================
# SPOTIFY EMBED SCRAPER
# ==============================================================================

_EMBED_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

def detect_spotify_type(url):
    for kind in ("playlist", "album"):
        m = re.search(rf'{kind}/([a-zA-Z0-9]+)', url)
        if m:
            return kind, m.group(1)
    return None, None

def scrape_spotify_tracks(url):
    kind, sid = detect_spotify_type(url)
    if not kind:
        console.print("[red]Invalid Spotify URL. Must be a playlist or album link.[/red]")
        sys.exit(1)
    embed_url = f"https://open.spotify.com/embed/{kind}/{sid}"
    with console.status(f"[green]Fetching {kind} from Spotify...[/green]"):
        resp = requests.get(embed_url, headers=_EMBED_HEADERS, timeout=15)
        resp.raise_for_status()
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
                  resp.text, re.DOTALL)
    if not m:
        console.print("[red]Could not parse Spotify embed page.[/red]")
        sys.exit(1)
    data   = json.loads(m.group(1))
    tracks = []
    try:
        entity    = data["props"]["pageProps"]["state"]["data"]["entity"]
        album_name = entity.get("name", "")
        covers    = entity.get("coverArt", {}).get("sources", [])
        album_art = (sorted(covers, key=lambda x: x.get("width", 0), reverse=True)[0]["url"]
                     if covers else "")
        for item in entity.get("trackList", []):
            title    = item.get("title", "").strip()
            subtitle = item.get("subtitle", "").strip()
            img_src  = item.get("album", {}).get("coverArt", {}).get("sources", [])
            cover    = (sorted(img_src, key=lambda x: x.get("width", 0), reverse=True)[0]["url"]
                        if img_src else album_art)
            if title:
                tracks.append({"title": title, "artist": subtitle,
                                "album": album_name, "cover_url": cover})
    except (KeyError, TypeError):
        tracks = _scrape_recursive(data)
    return tracks, kind

def _scrape_recursive(data, depth=0):
    tracks = []
    if depth > 10: return tracks
    if isinstance(data, dict):
        if "title" in data and "subtitle" in data and isinstance(data["title"], str):
            tracks.append({"title": data["title"], "artist": data.get("subtitle", ""),
                           "album": "", "cover_url": ""})
        else:
            for v in data.values():
                tracks.extend(_scrape_recursive(v, depth + 1))
    elif isinstance(data, list):
        for item in data:
            tracks.extend(_scrape_recursive(item, depth + 1))
    return tracks

# ==============================================================================
# YT-DLP DOWNLOAD
# ==============================================================================

def yt_download(artist, title, output_dir):
    query    = f"{artist} - {title}" if artist else title
    template = os.path.join(output_dir, "%(title)s.%(ext)s")
    cmd = [
        "yt-dlp", "--extract-audio", "--audio-format", "mp3",
        "--audio-quality", "0", "--no-playlist",
        "--match-filter", "duration < 600",
        "-o", template,
        "--print", "after_move:filepath",
        "--quiet", "--no-warnings",
        f"ytsearch1:{query}",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0: return None
    path = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else None
    if path and os.path.exists(path): return path
    try:
        mp3s = [os.path.join(output_dir, f)
                for f in os.listdir(output_dir) if f.endswith(".mp3")]
        return max(mp3s, key=os.path.getmtime) if mp3s else None
    except Exception:
        return None

# ==============================================================================
# PROGRESS BAR
# ==============================================================================

def make_progress():
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold green]{task.description}"),
        BarColumn(bar_width=30),
        TaskProgressColumn(),
        TextColumn("[dim]{task.fields[status]}[/dim]"),
        TimeRemainingColumn(),
        console=console,
    )

# ==============================================================================
# MODE 1 -- DOWNLOAD
# ==============================================================================

def mode_download(url="", output_dir=""):
    _cls()
    console.print(Panel(
        "[bold green]Download[/bold green]  [dim]Spotify -> YouTube -> MP3[/dim]",
        expand=False, border_style="bright_black", padding=(0, 2),
    ))
    console.print()
    if not url:
        url = Prompt.ask(
            "[cyan]Paste Spotify playlist or album URL[/cyan]  [dim](b = back)[/dim]",
            default="").strip()
        if url.lower() == "b": return
    if not output_dir:
        default_music = os.path.join(os.path.expanduser("~"), "Music")
        ans = Prompt.ask(
            "[cyan]Output folder[/cyan]  [dim](b = back)[/dim]",
            default=default_music).strip()
        if ans.lower() == "b": return
        output_dir = os.path.expandvars(os.path.expanduser(ans))
    else:
        output_dir = os.path.expandvars(os.path.expanduser(output_dir))

    os.makedirs(output_dir, exist_ok=True)
    console.print(f"\n[dim]Saving to:[/dim] [bold]{output_dir}[/bold]\n")

    tracks, kind = scrape_spotify_tracks(url)
    if not tracks:
        console.print("[red]No tracks found. Playlist/album may be private.[/red]")
        return

    table = Table(
        title=f"[bold green]{kind.capitalize()} -- {len(tracks)} tracks[/bold green]",
        show_header=True, header_style="bold green", border_style="dim",
    )
    table.add_column("#",      style="dim",        width=4)
    table.add_column("Title",  style="bold white", min_width=22)
    table.add_column("Artist", style="cyan",       min_width=18)
    for i, t in enumerate(tracks, 1):
        table.add_row(str(i), t["title"], t["artist"])
    console.print(table)
    console.print()

    if not confirm(f"Download all {len(tracks)} tracks?"):
        console.print("[dim]  Cancelled.[/dim]"); return

    console.print()
    failed = []

    with make_progress() as progress:
        overall = progress.add_task(f"Overall ({len(tracks)} songs)",
                                    total=len(tracks), status="")
        for track in tracks:
            label = f"{track['artist']} -- {track['title']}"
            label = label[:40] if len(label) <= 40 else label[:37] + "..."
            progress.update(overall, status=f"[cyan]{label}[/cyan]")
            task = progress.add_task(f"  [dim]{label}[/dim]", total=4, status="")

            progress.update(task, advance=1, status="downloading...")
            filepath = yt_download(track["artist"], track["title"], output_dir)
            if not filepath:
                progress.update(task, advance=3, status="[red]failed[/red]")
                failed.append(track); progress.update(overall, advance=1); continue

            progress.update(task, advance=1, status="tagging...")
            meta = {"title": track["title"], "artist": track["artist"],
                    "album": track["album"], "year": "", "track": "", "genre": "Music"}
            write_tags(filepath, meta, None, [], "")
            progress.update(task, advance=2, status="[green]done[/green]")
            progress.update(overall, advance=1)
            time.sleep(0.15)

    success = len(tracks) - len(failed)
    failed_text = ("\n\n[red]Failed:[/red]\n" +
                   "\n".join(f"  - {t['artist']} -- {t['title']}" for t in failed)
                   ) if failed else ""
    console.print()
    console.print(Panel(
        f"[green]{success}/{len(tracks)} songs downloaded[/green]\n"
        f"[dim]{output_dir}[/dim]{failed_text}",
        border_style="bright_black", padding=(0, 2),
    ))
    console.print()
    console.print(Panel(
        "[bold green]Auto-fixing metadata...[/bold green]  [dim]Spotify art + lyrics[/dim]",
        expand=False, border_style="bright_black", padding=(0, 2),
    ))
    console.print()
    mode_fix(folder=output_dir, dry_run=False, _return_to_menu=False)

# ==============================================================================
# MODE 2 -- FIX METADATA
# ==============================================================================

def fix_one(filepath, dry_run, progress, task_id):
    result = {"file": filepath, "ok": False, "art": False, "synced": False, "plain": False}
    existing = read_tags(filepath)
    artist   = existing["artist"]
    title    = existing["title"]
    if not artist or not title:
        fa, ft = guess_from_filename(filepath)
        artist = artist or fa
        title  = title  or ft
    if not title:
        progress.update(task_id, advance=4, status="[yellow]no title[/yellow]")
        return result

    progress.update(task_id, advance=1, status="looking up...")
    meta = best_meta(artist, title, existing)

    progress.update(task_id, advance=1, status="fetching art...")
    cover_data = fetch_thumbnail(meta["art_url"])
    result["art"] = bool(cover_data)

    progress.update(task_id, advance=1, status="fetching lyrics...")
    synced, plain = fetch_lyrics(meta["artist"], meta["title"])
    result["synced"] = bool(synced)
    result["plain"]  = bool(plain)

    progress.update(task_id, advance=0, status="saving...")
    if not dry_run:
        result["ok"] = write_tags(filepath, meta, cover_data, synced, plain)
    else:
        result["ok"] = True

    icons = ("art " if cover_data else "") + ("lyrics " if plain else "") + ("synced" if synced else "")
    progress.update(task_id, advance=1,
                    status=f"[green]done[/green] {icons}" if result["ok"] else "[red]failed[/red]")
    return result

def mode_fix(folder="", dry_run=False, _return_to_menu=True):
    _cls()
    console.print(Panel(
        "[bold green]Fix Metadata[/bold green]  [dim]Wipe & rewrite tags, art, lyrics[/dim]",
        expand=False, border_style="bright_black", padding=(0, 2),
    ))
    console.print()

    with console.status("[dim]Connecting to Spotify...[/dim]"):
        tok = get_spotify_token()
    console.print("[dim]  Spotify OK[/dim]\n" if tok else
                  "[dim]  Spotify unavailable -- using iTunes fallback[/dim]\n")

    if not folder:
        default_music = os.path.join(os.path.expanduser("~"), "Music")
        ans = Prompt.ask(
            "[cyan]Folder with MP3 files[/cyan]  [dim](b = back)[/dim]",
            default=default_music).strip()
        if ans.lower() == "b": return
        folder = os.path.expandvars(os.path.expanduser(ans))
    else:
        folder = os.path.expandvars(os.path.expanduser(folder))

    if not os.path.isdir(folder):
        console.print(f"[red]Not a directory: {folder}[/red]"); return

    mp3s = sorted(os.path.join(folder, f)
                  for f in os.listdir(folder) if f.lower().endswith(".mp3"))
    if not mp3s:
        console.print(f"[yellow]No MP3s found in {folder}[/yellow]"); return

    if dry_run:
        console.print("[dim]  Dry run -- no files will be changed[/dim]\n")

    table = Table(show_header=True, header_style="bold green", border_style="dim")
    table.add_column("#",      style="dim",        width=4)
    table.add_column("File",   style="bold white", min_width=26)
    table.add_column("Artist", style="cyan",       min_width=14)
    table.add_column("Title",  style="white",      min_width=14)
    for i, f in enumerate(mp3s, 1):
        tags = read_tags(f)
        fa, ft = guess_from_filename(f)
        table.add_row(str(i), os.path.basename(f),
                      tags["artist"] or fa or "[dim]?[/dim]",
                      tags["title"]  or ft or "[dim]?[/dim]")
    console.print(table)
    console.print()

    if not confirm(f"Fix all {len(mp3s)} files?"):
        console.print("[dim]  Cancelled.[/dim]"); return

    console.print()
    results = []

    with make_progress() as progress:
        overall = progress.add_task(f"Overall ({len(mp3s)} files)",
                                    total=len(mp3s), status="")
        for filepath in mp3s:
            name  = os.path.basename(filepath)
            label = name[:36] if len(name) <= 36 else name[:33] + "..."
            progress.update(overall, status=f"[cyan]{label}[/cyan]")
            ft = progress.add_task(f"  [dim]{label}[/dim]", total=4, status="")
            results.append(fix_one(filepath, dry_run, progress, ft))
            progress.update(overall, advance=1)
            time.sleep(0.1)

    ok    = sum(1 for r in results if r["ok"])
    art   = sum(1 for r in results if r["art"])
    syn   = sum(1 for r in results if r["synced"])
    plain = sum(1 for r in results if r["plain"])
    fail  = [r for r in results if not r["ok"]]
    fail_txt = ("\n\n[red]Failed:[/red]\n" +
                "\n".join(f"  - {os.path.basename(r['file'])}" for r in fail)) if fail else ""

    console.print()
    console.print(Panel(
        f"[green]{ok}/{len(mp3s)} fixed[/green]   "
        f"[dim]{art} art  {plain} lyrics  {syn} synced[/dim]\n"
        f"[dim]{folder}[/dim]"
        + ("[yellow]  (dry run)[/yellow]" if dry_run else "")
        + fail_txt,
        border_style="bright_black", padding=(0, 2),
    ))

# ==============================================================================
# MAIN MENU
# ==============================================================================

def main_menu():
    while True:
        _cls()
        console.print(Panel(
            "[bold green]Music Tool[/bold green]\n\n"
            "  [bold white]1[/bold white]  [dim]Download[/dim]   Spotify playlist or album -> MP3\n"
            "  [bold white]2[/bold white]  [dim]Fix Tags[/dim]   Rewrite metadata + Spotify art + lyrics\n"
            "  [bold white]q[/bold white]  [dim]Quit[/dim]",
            expand=False, border_style="bright_black", padding=(1, 4),
        ))
        console.print()
        choice = Prompt.ask("[dim]>[/dim]", choices=["1", "2", "q"], default="1")
        if choice == "1":
            mode_download()
        elif choice == "2":
            dry = confirm("Dry run (preview only)?", default=False)
            mode_fix(dry_run=dry)
            console.print("\n[dim]Press Enter to return to menu...[/dim]")
            input()
        elif choice == "q":
            console.print("[dim]Bye![/dim]")
            break

def main():
    # Check system deps
    missing = check_system_deps()
    if missing:
        install_system_deps(missing)
    
    args = sys.argv[1:]
    if not args:
        main_menu()
        return
    cmd  = args[0].lower()
    rest = args[1:]
    if cmd == "download":
        mode_download(rest[0] if rest else "", rest[1] if len(rest) > 1 else "")
    elif cmd == "fix":
        mode_fix(rest[0] if rest else "", "--dry" in rest)
    else:
        console.print(f"[red]Unknown command: {cmd}[/red]")
        console.print("[dim]Usage: python music.py [download|fix][/dim]")

if __name__ == "__main__":
    log_file = pathlib.Path.home() / "music_tool_crash.log"
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n\n[dim]Interrupted. Goodbye![/dim]\n")
    except Exception as e:
        err = traceback.format_exc()
        console.print(f"\n[red]Crash: {e}[/red]")
        console.print(f"[dim]Log saved to: {log_file}[/dim]")
        log_file.write_text(err)
        console.print("\n[dim]Press Enter to exit...[/dim]")
        input()
