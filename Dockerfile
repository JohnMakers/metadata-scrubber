# Minimal Python image
FROM python:3.11-slim

# 1) Install system deps (ExifTool) for accurate metadata scrubbing
RUN apt-get update \
 && apt-get install -y --no-install-recommends exiftool \
 && rm -rf /var/lib/apt/lists/*

# 2) App setup
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# 3) Copy source
COPY . .

# 4) Entrypoint (Render/containers will pass PORT env var)
ENV PYTHONUNBUFFERED=1
ENV PORT=8000
EXPOSE 8000
CMD ["uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8000"]
