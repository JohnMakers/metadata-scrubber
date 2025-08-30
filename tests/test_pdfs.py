# tests/test_pdfs.py
from pathlib import Path
import pikepdf
import subprocess
from app.cleaners.pdfs import clean_pdf

def _has_pdf_meta(path: Path) -> bool:
    out = subprocess.run(["exiftool", str(path)], capture_output=True, text=True, check=True).stdout
    lines = [ln for ln in out.splitlines() if not ln.startswith(("File ", "System "))]
    return any(lines)

def test_pdf_clean(tmp_path: Path):
    src = tmp_path / "a.pdf"
    dst = tmp_path / "a_clean.pdf"

    # Create a trivial single-page PDF with pikepdf
    with pikepdf.new() as pdf:
        # One blank page
        pdf.pages.append(pikepdf.Page.new())
        pdf.save(src)

    # Add author metadata and a tiny JS entry
    subprocess.run(["exiftool", "-Author=Carol", "-overwrite_original_in_place", str(src)], check=True)
    with pikepdf.open(src) as pdf:
        # Add JS name tree
        pdf.root["/Names"] = pikepdf.Dictionary({
            "/JavaScript": pikepdf.Dictionary()
        })
        pdf.save(src)

    # Ensure metadata present
    assert _has_pdf_meta(src) is True

    # Clean
    clean_pdf(src, dst)
    assert dst.exists()
    assert _has_pdf_meta(dst) is False

    # Also ensure no JavaScript remains
    with pikepdf.open(dst) as pdf:
        assert "/Names" not in pdf.root or "/JavaScript" not in pdf.root["/Names"]
