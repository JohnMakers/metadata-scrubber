# app/server.py
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import shutil
import uuid
import os

from app.settings import UPLOAD_DIR, OUTPUT_DIR, ALLOWED_EXTENSIONS, MAX_FILE_SIZE
from app.utils.cleanup import cleanup_once, start_background_cleanup
from app.cleaners.images import clean_image
from app.cleaners.office import clean_office
from app.cleaners.pdfs import clean_pdf

app = FastAPI(title="Aintivirus Metadata Remover (MVP)")

# Serve static frontend
app.mount("/static", StaticFiles(directory=str(Path(__file__).resolve().parent.parent / "static")), name="static")

@app.on_event("startup")
def bootstrap():
    # Start background cleaner
    start_background_cleanup(interval_seconds=120)

@app.get("/", response_class=HTMLResponse)
def home():
    index_path = Path(__file__).resolve().parent.parent / "static" / "index.html"
    return index_path.read_text(encoding="utf-8")

def _secure_ext(filename: str) -> str:
    return Path(filename).suffix.lower()

def _enforce_size_limit(upload_file: UploadFile) -> bytes:
    data = upload_file.file.read()
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail=f"File too large. Limit is {MAX_FILE_SIZE} bytes.")
    return data

def _choose_cleaner(ext: str):
    if ext in {".jpg", ".jpeg", ".png", ".gif", ".tif", ".tiff"}:
        return "image"
    if ext in {".docx", ".xlsx"}:
        return "office"
    if ext in {".pdf"}:
        return "pdf"
    raise HTTPException(status_code=400, detail="Unsupported file type for this MVP.")

@app.post("/clean")
def clean(upload: UploadFile = File(...)):
    """
    1) Check extension and size
    2) Save to uploads
    3) Clean into outputs
    4) Return a download link
    """
    ext = _secure_ext(upload.filename)
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Extension {ext} not allowed for this MVP.")

    data = _enforce_size_limit(upload)
    # Create unique filenames to avoid collisions
    uid = uuid.uuid4().hex
    src_path = UPLOAD_DIR / f"{uid}{ext}"
    dst_path = OUTPUT_DIR / f"{uid}_clean{ext}"

    # Write original upload to disk
    src_path.write_bytes(data)

    # Run cleanup (defense-in-depth)
    cleaner = _choose_cleaner(ext)
    try:
        if cleaner == "image":
            clean_image(src_path, dst_path)
        elif cleaner == "office":
            clean_office(src_path, dst_path)
        elif cleaner == "pdf":
            clean_pdf(src_path, dst_path)
        else:
            raise HTTPException(status_code=500, detail="Unknown cleaner.")
    except FileNotFoundError as e:
        # Common when exiftool isn't installed
        raise HTTPException(status_code=500, detail="Server missing dependency (exiftool). Please install and restart.") from e
    except Exception as e:
        # On failure, remove partial outputs if any
        if dst_path.exists():
            dst_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Cleaning failed: {e!s}") from e
    finally:
        # Trigger a quick cleanup pass (best effort)
        cleanup_once()

    # Send a nice filename for the browser download prompt
    proposed_name = f"{Path(upload.filename).stem}_clean{ext}"
    return {
        "download": f"/download/{dst_path.name}",
        "suggested_filename": proposed_name
    }

@app.get("/download/{name}")
def download(name: str):
    path = OUTPUT_DIR / name
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found (maybe it expired and was deleted).")
    # Force "download" behavior with correct filename
    return FileResponse(path, media_type="application/octet-stream", filename=name)
