# app/settings.py
from pathlib import Path
import os
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"

UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 500 * 1024 * 1024))
RETENTION = timedelta(minutes=2)

# Allowed extensions (v2 includes videos)
ALLOWED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".tif", ".tiff", ".webp", # <-- .webp ADDED HERE
    ".docx", ".xlsx", ".pdf",
    ".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm"
}

