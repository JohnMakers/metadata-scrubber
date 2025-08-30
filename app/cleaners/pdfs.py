# app/cleaners/pdfs.py
"""
PDF cleaning using pypdf (pure Python, Windows-friendly):
- Remove /Info and XMP (/Metadata)
- Remove JavaScript entries from the Names tree
- Remove all page annotations (/Annots)
- Then run ExifTool to strip any lingering tags (defense-in-depth)

We do not alter visible text/pixels—only metadata/annotations/scripts.
"""
from pathlib import Path
import subprocess
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject

def _strip_root_metadata(writer: PdfWriter) -> None:
    # Delete XMP metadata (/Metadata) if present
    root = writer._root_object  # low-level access is fine for this task
    meta_key = NameObject("/Metadata")
    if meta_key in root:
        del root[meta_key]
    # Clear document info dictionary
    writer.add_metadata({})  # sets an empty info dict

def _remove_names_javascript(writer: PdfWriter) -> None:
    root = writer._root_object
    names_key = NameObject("/Names")
    if names_key in root:
        names = root[names_key]
        # Names dictionary can contain /JavaScript
        js_key = NameObject("/JavaScript")
        if js_key in names:
            del names[js_key]
        # If Names becomes empty, you could remove it entirely (optional)

def _remove_page_annotations(page) -> None:
    ann_key = NameObject("/Annots")
    if ann_key in page:
        del page[ann_key]

def _pypdf_sanitize(src: Path, dst: Path) -> None:
    reader = PdfReader(str(src))
    writer = PdfWriter()

    # Copy pages while stripping page-level annotations
    for page in reader.pages:
        _remove_page_annotations(page)
        writer.add_page(page)

    # Remove document-level XMP, Info, and JavaScript
    _strip_root_metadata(writer)
    _remove_names_javascript(writer)

    with open(dst, "wb") as f:
        writer.write(f)

def _exiftool_strip_all(path: Path) -> None:
    subprocess.run(
        ["exiftool", "-all=", "-overwrite_original_in_place", str(path)],
        check=True,
        capture_output=True
    )

def clean_pdf(src: Path, dst: Path) -> None:
    # First pass: structural sanitize with pypdf
    _pypdf_sanitize(src, dst)
    # Second pass: exiftool to strip any lingering metadata tags
    _exiftool_strip_all(dst)
