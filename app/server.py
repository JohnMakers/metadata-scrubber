# app/server.py
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from app.cleaners.videos import clean_video
from pathlib import Path
import shutil
import uuid
import os
import zipfile
import subprocess
from typing import List
from app.utils.signature import detect_extension, ext_equivalent
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

def _enforce_size_limit(data: bytes) -> None:
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail=f"File too large. Limit is {MAX_FILE_SIZE} bytes.")

def _verify_signature(data: bytes, filename: str) -> None:
    claimed = Path(filename).suffix.lower()
    detected = detect_extension(data)
    if detected is None:
        raise HTTPException(status_code=400, detail="Unsupported or unrecognized file signature.")
    if not ext_equivalent(claimed, detected):
        raise HTTPException(
            status_code=400,
            detail=f"Extension spoofing detected: file looks like {detected} but was uploaded as {claimed}."
        )

def _choose_cleaner(ext: str):
    if ext in {".jpg", ".jpeg", ".png", ".gif", ".tif", ".tiff"}:
        return "image"
    if ext in {".docx", ".xlsx"}:
        return "office"
    if ext in {".pdf"}:
        return "pdf"
    if ext in {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm"}:
        return "video"
    raise HTTPException(status_code=400, detail="Unsupported file type for this MVP.")

@app.post("/clean-batch")
async def clean_batch(uploads: List[UploadFile] = File(...)):
    if not uploads:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    results = []
    uid = uuid.uuid4().hex
    for up in uploads:
        ext = _secure_ext(up.filename)
        if ext not in ALLOWED_EXTENSIONS:
            # Skip invalid files in a batch context or raise an error
            continue

        data = await up.read()
        _enforce_size_limit(data)
        _verify_signature(data, up.filename)

        src_path = UPLOAD_DIR / f"{uid}_{uuid.uuid4().hex}{ext}"
        dst_path = OUTPUT_DIR / f"{uid}_{Path(up.filename).stem}_clean{ext}"
        src_path.write_bytes(data)

        try:
            cleaner = _choose_cleaner(ext)
            if cleaner == "image":
                clean_image(src_path, dst_path)
            elif cleaner == "office":
                clean_office(src_path, dst_path)
            elif cleaner == "pdf":
                clean_pdf(src_path, dst_path)
            elif cleaner == "video":
                clean_video(src_path, dst_path)
            
            results.append({
                "orig": up.filename,
                "cleaned_name": dst_path.name,
                "download": f"/download/{dst_path.name}"
            })
        except Exception as e:
            # Optionally log the error and continue with other files
            print(f"Failed to clean {up.filename}: {e}")
        finally:
            cleanup_once()

    if not results:
         raise HTTPException(status_code=400, detail="All uploaded files were invalid or failed to process.")

    # Single file success: mirror /clean response for convenience
    if len(results) == 1:
        item = results[0]
        return {
            "download": item["download"],
            "suggested_filename": item["cleaned_name"],
            "items": results
        }

    # Multiple: build a ZIP in outputs
    zip_name = f"{uid}_cleaned_files.zip"
    zip_path = OUTPUT_DIR / zip_name
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for item in results:
            file_path = OUTPUT_DIR / item["cleaned_name"]
            if file_path.exists():
                z.write(file_path, arcname=item["cleaned_name"])

    return {
        "zip_download": f"/download/{zip_name}",
        "items": results,
        "count": len(results)
    }


@app.post("/inspect")
async def inspect(upload: UploadFile = File(...)):
    ext = Path(upload.filename).suffix.lower()
    data = await upload.read()
    tmp = UPLOAD_DIR / f"inspect_{uuid.uuid4().hex}{ext}"
    tmp.write_bytes(data)
    try:
        out = subprocess.run(["exiftool", str(tmp)], check=True, capture_output=True, text=True).stdout
        return {"report": out}
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Server missing exiftool.")
    finally:
        if tmp.exists():
            tmp.unlink()

@app.get("/download/{name}")
def download(name: str):
    path = OUTPUT_DIR / name
    if not path.is_file(): # More secure check
        raise HTTPException(status_code=404, detail="File not found (maybe it expired and was deleted).")
    return FileResponse(path, media_type="application/octet-stream", filename=name)

@app.get("/inspect-output/{name}")
def inspect_output(name: str):
    path = OUTPUT_DIR / name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="File not found (maybe expired).")
    try:
        out = subprocess.run(["exiftool", str(path)], check=True, capture_output=True, text=True).stdout
        return {"report": out}
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Server missing exiftool.")
