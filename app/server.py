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

app.mount("/static", StaticFiles(directory=str(Path(__file__).resolve().parent.parent / "static")), name="static")

@app.on_event("startup")
def bootstrap():
    start_background_cleanup(interval_seconds=120)

@app.get("/", response_class=HTMLResponse)
def home():
    index_path = Path(__file__).resolve().parent.parent / "static" / "index.html"
    return index_path.read_text(encoding="utf-8")

def _secure_ext(filename: str) -> str:
    return Path(filename).suffix.lower()

async def _validate_and_read(upload_file: UploadFile):
    ext = _secure_ext(upload_file.filename)
    if ext not in ALLOWED_EXTENSIONS:
        return None, f"Extension {ext} not allowed."
    
    data = await upload_file.read()
    
    if len(data) > MAX_FILE_SIZE:
        return None, f"File too large. Limit is {MAX_FILE_SIZE} bytes."
        
    _verify_signature(data, upload_file.filename)
    return data, None

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
    if ext in {".jpg", ".jpeg", ".png", ".gif", ".tif", ".tiff", ".webp"}: # <-- .webp ADDED HERE
        return "image"
    if ext in {".docx", ".xlsx"}:
        return "office"
    if ext in {".pdf"}:
        return "pdf"
    if ext in {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm"}:
        return "video"
    return None

@app.post("/clean-batch")
async def clean_batch(uploads: List[UploadFile] = File(...)):
    if not uploads:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    results = []
    uid = uuid.uuid4().hex
    for up in uploads:
        data, error_detail = await _validate_and_read(up)
        if error_detail:
            # For simplicity in a batch, we can skip failed files. 
            # In a real app, you might return specific errors per file.
            continue 

        ext = _secure_ext(up.filename)
        src_path = UPLOAD_DIR / f"{uid}_{uuid.uuid4().hex}{ext}"
        dst_path = OUTPUT_DIR / f"{uid}_{Path(up.filename).stem}_clean{ext}"
        src_path.write_bytes(data)

        try:
            cleaner_type = _choose_cleaner(ext)
            if cleaner_type == "image":
                clean_image(src_path, dst_path)
            elif cleaner_type == "office":
                clean_office(src_path, dst_path)
            elif cleaner_type == "pdf":
                clean_pdf(src_path, dst_path)
            elif cleaner_type == "video":
                clean_video(src_path, dst_path)
            else:
                continue # Skip unsupported but allowed types

            results.append({
                "orig": up.filename,
                "cleaned_name": dst_path.name,
                "download": f"/download/{dst_path.name}"
            })
        except Exception as e:
            print(f"Error cleaning {up.filename}: {e}") # Log error
        finally:
            cleanup_once()

    if not results:
        raise HTTPException(status_code=400, detail="All uploaded files were invalid or failed to process.")

    if len(results) == 1:
        item = results[0]
        return {
            "download": item["download"],
            "suggested_filename": item["cleaned_name"],
            "items": results
        }

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
    data = await upload.read()
    ext = _secure_ext(upload.filename)
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
    if not path.is_file():
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
