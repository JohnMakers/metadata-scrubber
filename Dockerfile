FROM python:3.11-slim

# ExifTool + FFmpeg
RUN apt-get update \
 && apt-get install -y --no-install-recommends exiftool ffmpeg \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["sh","-c","uvicorn app.server:app --host 0.0.0.0 --port ${PORT:-8000}"]
