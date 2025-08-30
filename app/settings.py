# ...
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 500 * 1024 * 1024))  # 500 MB default
# ...
ALLOWED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".tif", ".tiff",
    ".docx", ".xlsx", ".pdf",
    ".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm"  # v2 videos
}
