# app/cleaners/office.py
"""
DOCX/XLSX cleaning:
- Use ExifTool to strip XMP/core properties reliably.
- Additionally, remove OOXML 'docProps' and known comments/revisions parts for safety,
  without altering document content. We operate on a copy (dst).
NOTE: Fully "accepting tracked changes" is complex; we *remove* revision markup files
      and comments parts so that personal notes aren't retained. The visible text is not altered.
"""
import subprocess
from pathlib import Path
import zipfile
from io import BytesIO

_OOXML_PROP_PATHS = {
    "docx": ["docProps/core.xml", "docProps/app.xml"],
    "xlsx": ["docProps/core.xml", "docProps/app.xml"]
}

# Known comment parts (remove if present)
_COMMENT_PARTS = {
    "docx": ["word/comments.xml", "word/commentsExtended.xml"],
    "xlsx": ["xl/comments.xml", "xl/comments1.xml", "xl/comments2.xml"]
}

# Known revisions parts (remove if present)
_REVISION_PARTS = {
    "docx": ["word/revisions", "word/trackChanges", "word/editors.xml"],
    "xlsx": ["xl/revisions", "xl/commentsExt.xml"]
}

def _ooxtype(path: Path) -> str | None:
    ext = path.suffix.lower()
    if ext == ".docx":
        return "docx"
    if ext == ".xlsx":
        return "xlsx"
    return None

def _strip_with_exiftool(path: Path) -> None:
    subprocess.run(
        ["exiftool", "-all=", "-overwrite_original_in_place", str(path)],
        check=True,
        capture_output=True
    )

def _zip_remove_members(src_path: Path, to_remove: list[str], dst_path: Path) -> None:
    with zipfile.ZipFile(src_path, "r") as zin:
        with zipfile.ZipFile(dst_path, "w", compression=zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                if item.filename in to_remove or any(item.filename.startswith(prefix + "/") for prefix in to_remove):
                    # Skip writing this member = effectively delete
                    continue
                data = zin.read(item.filename)
                zout.writestr(item, data)

def clean_office(src: Path, dst: Path) -> None:
    # Work on a copy
    dst.write_bytes(src.read_bytes())
    kind = _ooxtype(dst)
    if not kind:
        raise ValueError("Unsupported OOXML type")

    # 1) ExifTool strip XMP, core/app properties, etc.
    _strip_with_exiftool(dst)

    # 2) Remove OOXML parts that could still hold properties/comments/revisions
    to_remove = set(_OOXML_PROP_PATHS[kind]) | set(_COMMENT_PARTS[kind]) | set(_REVISION_PARTS[kind])
    # Re-pack zip without those entries
    # Use an in-memory temp to avoid partially written files on error
    tmp_bytes = BytesIO()
    with zipfile.ZipFile(dst, "r") as zin:
        with zipfile.ZipFile(tmp_bytes, "w", compression=zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                if item.filename in to_remove or any(item.filename.startswith(prefix + "/") for prefix in to_remove):
                    continue
                zout.writestr(item, zin.read(item.filename))
    dst.write_bytes(tmp_bytes.getvalue())
