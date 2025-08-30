# tests/test_images.py
"""
These tests assume exiftool is installed on the system.
We create a simple image, inject a fake metadata tag via exiftool,
run the API cleaner function directly, then assert metadata is gone.
"""
from pathlib import Path
from PIL import Image
import subprocess
from app.cleaners.images import clean_image

def _has_metadata(path: Path) -> bool:
    # If exiftool outputs any tag lines (excluding File: and System:), we consider it "has metadata"
    out = subprocess.run(["exiftool", str(path)], capture_output=True, text=True, check=True).stdout
    lines = [ln for ln in out.splitlines() if not ln.startswith(("File ", "System "))]
    return any(lines)

def test_jpeg_clean_tmp(tmp_path: Path):
    src = tmp_path / "img.jpg"
    dst = tmp_path / "img_clean.jpg"

    # Create a simple image
    Image.new("RGB", (32, 32), color=(123, 200, 50)).save(src)

    # Add fake metadata
    subprocess.run(["exiftool", "-Artist=Alice", "-overwrite_original_in_place", str(src)], check=True)

    assert _has_metadata(src) is True

    # Clean
    clean_image(src, dst)
    assert dst.exists()

    # Should have no metadata now
    assert _has_metadata(dst) is False
