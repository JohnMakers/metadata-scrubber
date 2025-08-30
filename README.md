# Aintivirus Metadata Remover (MVP)

## Run locally
1. Create venv:
   - Windows: `python -m venv .venv && .venv\Scripts\activate`
   - macOS/Linux: `python3 -m venv .venv && source .venv/bin/activate`
2. Install deps: `pip install -r requirements.txt`
3. Run server: `uvicorn app.server:app --reload`
4. Open: http://127.0.0.1:8000/

## Notes
- Requires `exiftool` installed on your system.
- Files auto-delete ~20 minutes after upload.
- Output is named `*_clean.ext`.

## Testing
`pytest -q`
