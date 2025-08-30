# app/utils/signature.py
"""
Lightweight magic-number / structure checks to prevent extension-spoofed uploads.
We accept only formats we can clean. If the on-disk extension doesn't match the
detected format (within an equivalence group), we reject the file.

Supported families:
- Images: JPG/JPEG, PNG, GIF, TIFF
- Office: DOCX (ZIP with 'word/'), XLSX (ZIP with 'xl/')
- PDF
- Videos: MP4/MOV/M4V (ISO-BMFF), AVI (RIFF/AVI), MKV/WEBM (Matroska/EBML)
"""

from __future__ import annotations
from zipfile import ZipFile, BadZipFile
from pathlib import Path

def _starts(data: bytes, prefix: bytes) -> bool:
    return data.startswith(prefix)

def _has(data: bytes, offset: int, token: bytes) -> bool:
    return data[offset:offset+len(token)] == token

# --- Image checks ---
def _is_jpeg(data: bytes) -> bool:
    return _starts(data, b"\xFF\xD8\xFF")

def _is_png(data: bytes) -> bool:
    return _starts(data, b"\x89PNG\r\n\x1a\n")

def _is_gif(data: bytes) -> bool:
    return _starts(data, b"GIF87a") or _starts(data, b"GIF89a")

def _is_tiff(data: bytes) -> bool:
    return _starts(data, b"MM\x00*") or _starts(data, b"II*\x00")

# --- PDF ---
def _is_pdf(data: bytes) -> bool:
    return _starts(data, b"%PDF-")

# --- Office (OOXML = ZIP) ---
def _is_docx(data: bytes) -> bool:
    try:
        from io import BytesIO
        with ZipFile(BytesIO(data)) as z:
            return any(n.startswith("word/") for n in z.namelist())
    except BadZipFile:
        return False

def _is_xlsx(data: bytes) -> bool:
    try:
        from io import BytesIO
        with ZipFile(BytesIO(data)) as z:
            return any(n.startswith("xl/") for n in z.namelist())
    except BadZipFile:
        return False

# --- Video ---
def _is_iso_bmff(data: bytes) -> bool:
    # MP4/MOV/M4V: size(4) + 'ftyp' at bytes 4..8
    return len(data) >= 12 and _has(data, 4, b"ftyp")

def _is_avi(data: bytes) -> bool:
    # 'RIFF....AVI '
    return len(data) >= 12 and _starts(data, b"RIFF") and _has(data, 8, b"AVI ")

def _is_matroska(data: bytes) -> bool:
    # EBML header
    return _starts(data, b"\x1A\x45\xDF\xA3")

# Equivalence groups (same cleaner path)
_EQUIV = {
    "mp4": {"mp4", "mov", "m4v"},
    "mkv": {"mkv", "webm"},   # both Matroska container; webm is constrained matroska
}

def detect_extension(data: bytes) -> str | None:
    """Return a normalized extension (with dot), or None if unsupported."""
    if _is_jpeg(data): return ".jpg"
    if _is_png(data):  return ".png"
    if _is_gif(data):  return ".gif"
    if _is_tiff(data): return ".tiff"
    if _is_pdf(data):  return ".pdf"
    if _is_docx(data): return ".docx"
    if _is_xlsx(data): return ".xlsx"
    if _is_iso_bmff(data): return ".mp4"      # mp4/mov/m4v family
    if _is_avi(data):     return ".avi"
    if _is_matroska(data):return ".mkv"       # mkv/webm family
    return None

def ext_equivalent(a: str, b: str) -> bool:
    """True if extensions are the same or within an equivalence family."""
    a = a.lstrip(".").lower()
    b = b.lstrip(".").lower()
    if a == b: return True
    for fam in _EQUIV.values():
        if a in fam and b in fam:
            return True
    return False
