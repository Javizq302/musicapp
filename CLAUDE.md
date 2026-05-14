# Music Cover Embedder

## What is this?
A Python desktop app that batch-embeds cover art into audio files (FLAC/MP3) from ZIP bundles downloaded from music sites.

## How it works
1. User selects a folder with ZIPs and an output folder
2. Each ZIP contains a `cover.jpg` and 1-2 audio files (regular + optional extended mix)
3. The app extracts each ZIP, embeds the cover into the audio metadata, and copies the processed files to the output folder

## Tech stack
- **Python 3.14** with virtual environment (`venv/`)
- **customtkinter** — dark/minimal UI
- **mutagen** — audio metadata (ID3 for MP3, Vorbis for FLAC)
- **PyInstaller** — builds macOS `.app` executable

## Key files
- `app.py` — main application (UI + processing logic)
- `venv/` — virtual environment with dependencies
- `dist/MusicCoverEmbedder.app` — built macOS app

## Running
```bash
source venv/bin/activate
python app.py
```

## Building executable
```bash
source venv/bin/activate
pyinstaller --onefile --windowed --name "MusicCoverEmbedder" --clean app.py
```
Output: `dist/MusicCoverEmbedder.app`

## Notes
- Finder/Get Info doesn't show FLAC cover art, but it works correctly in Rekordbox and other DJ/music software
- Pyrefly linter needs `pyrefly.toml` to point to venv interpreter for import resolution
- ZIP structure: `cover.jpg` + 1-2 audio files (flat or one level of subdirectory)
