# app/settings.py
from pathlib import Path
import os
from datetime import timedelta

# Base directories for uploads/outputs. These are created if missing.
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"

# Create dirs on import to avoid race conditions.
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# Max file size (bytes). Since we're excluding video for MVP,
# 100 MB is generous for large PDFs/PNGs but still protects memory/costs.
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 100 * 1024 * 1024))  # 100 MB

# How long we keep files before auto-deleting
RETENTION = timedelta(minutes=20)

# Allowed extensions for MVP (videos excluded)
ALLOWED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".tif", ".tiff",
    ".docx", ".xlsx", ".pdf"
}
