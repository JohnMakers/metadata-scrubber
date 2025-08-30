# app/cleaners/images.py
"""
Image metadata cleaning:
1) Use ExifTool to remove ALL metadata (-all=).
2) For PNGs, also ensure textual chunks (tEXt, zTXt, iTXt) are gone by re-saving via Pillow.
   (ExifTool usually handles this, but the extra step is a belt-and-suspenders approach.)
"""
import subprocess
from pathlib import Path
from PIL import Image

def _run_exiftool_strip(src: Path, dst: Path) -> None:
    # ExifTool command:
    # -all= removes all metadata
    # -overwrite_original_in_place would change the file; here we write to a new file instead:
    # We copy bytes, then run exiftool to strip in-place on the copy.
    dst.write_bytes(src.read_bytes())
    subprocess.run(
        ["exiftool", "-all=", "-overwrite_original_in_place", str(dst)],
        check=True,
        capture_output=True
    )

def _is_png(path: Path) -> bool:
    return path.suffix.lower() == ".png"

def _reencode_png_remove_text_chunks(path: Path) -> None:
    # Open with Pillow and re-save, which drops non-essential chunks by default
    with Image.open(path) as im:
        # Convert to same mode to preserve pixels; save without text chunks
        # Pillow ignores/strips textual chunks unless explicitly provided
        im.save(path)

def clean_image(src: Path, dst: Path) -> None:
    _run_exiftool_strip(src, dst)
    if _is_png(dst):
        # Double-ensure textual chunks are gone
        _reencode_png_remove_text_chunks(dst)
