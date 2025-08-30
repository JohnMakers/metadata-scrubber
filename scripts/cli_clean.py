# scripts/cli_clean.py
r"""
CLI metadata scrubber (no web server needed).
Usage examples (from project root, with your venv activated):

  python scripts/cli_clean.py path/to/file.pdf
  python scripts/cli_clean.py C:\\Users\\you\\Desktop\\pic.jpg
  python scripts/cli_clean.py path/to/folder  (processes all supported files inside, recursively)

Outputs are written next to the originals as *_clean.ext
"""
from __future__ import annotations
import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))  # add project root to import path

import argparse
import sys
from pathlib import Path
import shutil
import subprocess
import argparse
import sys
from pathlib import Path

# --- ADD THIS SHIM: ensures "app" is importable even when running by path ---
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# ---------------------------------------------------------------------------

import shutil
import subprocess

# Reuse our existing cleaners
from app.settings import ALLOWED_EXTENSIONS
from app.cleaners.images import clean_image
from app.cleaners.office import clean_office
from app.cleaners.pdfs import clean_pdf

SUPPORTED = {".jpg", ".jpeg", ".png", ".gif", ".tif", ".tiff", ".docx", ".xlsx", ".pdf"}

def check_exiftool() -> None:
    """Ensure exiftool is installed and on PATH."""
    try:
        subprocess.run(["exiftool", "-ver"], check=True, capture_output=True, text=True)
    except Exception:
        print("❌ exiftool is not available on your system. Please install it and try again.")
        print("   Windows: https://exiftool.org/  (then reopen your terminal)")
        print("   macOS (Homebrew): brew install exiftool")
        sys.exit(1)

def choose_cleaner(ext: str):
    ext = ext.lower()
    if ext in {".jpg", ".jpeg", ".png", ".gif", ".tif", ".tiff"}:
        return clean_image
    if ext in {".docx", ".xlsx"}:
        return clean_office
    if ext == ".pdf":
        return clean_pdf
    return None

def clean_one(path: Path) -> Path | None:
    ext = path.suffix.lower()
    if ext not in SUPPORTED:
        print(f"• Skipping unsupported file: {path.name}")
        return None

    dst = path.with_name(f"{path.stem}_clean{ext}")
    cleaner = choose_cleaner(ext)
    try:
        cleaner(path, dst)
        print(f"✅ Cleaned: {path.name} → {dst.name}")
        return dst
    except Exception as e:
        print(f"❌ Failed to clean {path.name}: {e}")
        try:
            if dst.exists():
                dst.unlink(missing_ok=True)
        except Exception:
            pass
        return None

def iter_files(target: Path):
    if target.is_file():
        yield target
    else:
        for p in target.rglob("*"):
            if p.is_file() and p.suffix.lower() in SUPPORTED:
                yield p

def main():
    parser = argparse.ArgumentParser(description="Remove metadata from images and documents (no server needed).")
    parser.add_argument("path", help="File or folder to clean")
    args = parser.parse_args()

    root = Path(args.path).expanduser().resolve()
    if not root.exists():
        print(f"❌ Not found: {root}")
        sys.exit(1)

    check_exiftool()

    any_done = False
    for f in iter_files(root):
        res = clean_one(f)
        if res:
            any_done = True

    if not any_done:
        print("ℹ️ Nothing cleaned. Did you pass a supported file (jpg/png/gif/tiff/docx/xlsx/pdf)?")

if __name__ == "__main__":
    main()
