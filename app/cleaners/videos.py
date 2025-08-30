# app/cleaners/videos.py
"""
Video metadata cleaner (MP4/MOV/M4V/AVI/MKV/WebM).
Strategy:
  1) FFmpeg remux with stream copy to strip container/global metadata:
       -map 0           (keep all streams)
       -c copy          (no re-encode)
       -map_metadata -1 (drop all metadata)
       -movflags +faststart (nice for MP4 playback)
  2) ExifTool pass to nuke stragglers (QuickTime keys, GPS, time tags, XMP).
This preserves audio/video bytes and removes identifying metadata.
"""
from __future__ import annotations
from pathlib import Path
import subprocess
import shutil
import tempfile

_FFMPEG = ["ffmpeg", "-hide_banner", "-loglevel", "error"]
_EXIFTOOL = [
    "exiftool",
    "-all=",                    # nuke everything it knows
    "-Keys:all=",               # iOS/QuickTime keys
    "-Time:all=",               # creation/mod times in atoms
    "-GPS:all=",                # GPS & location clusters
    "-UserData:all=",
    "-ItemList:all=",
    "-QuickTime:LocationInformation=", 
    "-com.apple.quicktime.location.ISO6709=",  # iOS location atom
    "-overwrite_original_in_place",
]

def _ffmpeg_remux(src: Path, dst: Path) -> None:
    # Build an ffmpeg command that preserves streams but strips metadata.
    cmd = _FFMPEG + [
        "-y", "-i", str(src),
        "-map", "0",
        "-c", "copy",
        "-map_metadata", "-1",
        "-movflags", "+faststart",
        str(dst),
    ]
    subprocess.run(cmd, check=True)

def _exiftool_strip(path: Path) -> None:
    subprocess.run(_EXIFTOOL + [str(path)], check=True, capture_output=True)

def clean_video(src: Path, dst: Path) -> None:
    # Work in a temp file to avoid half-written outputs on error
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / f"tmp{src.suffix}"
        _ffmpeg_remux(src, tmp)
        shutil.copyfile(tmp, dst)
    # Defense-in-depth: run exiftool on the result
    _exiftool_strip(dst)
