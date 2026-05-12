"""
app/services/upload_service.py
==============================
Manages user uploads for inference.
Validates images, provides paths, and automatically cleans up old files.
"""

import os
import time
import logging
from pathlib import Path
from fastapi import UploadFile

logger = logging.getLogger(__name__)

UPLOAD_DIR = Path("backend/uploads")
MAX_FILE_SIZE_MB = 10
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
CLEANUP_AGE_SECONDS = 3600  # 1 hour


class UploadService:
    def __init__(self):
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    def validate_and_save(self, file: UploadFile) -> Path:
        """Validates extension/size and saves the file temporarily."""
        ext = Path(file.filename).suffix.lower() if file.filename else ""
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(f"Invalid file type. Allowed: {ALLOWED_EXTENSIONS}")

        file.file.seek(0, 2)
        size_mb = file.file.tell() / (1024 * 1024)
        file.file.seek(0)

        if size_mb > MAX_FILE_SIZE_MB:
            raise ValueError(f"File too large. Max size is {MAX_FILE_SIZE_MB}MB.")

        # Generate unique name
        unique_name = f"{int(time.time())}_{file.filename}"
        save_path = UPLOAD_DIR / unique_name

        with open(save_path, "wb") as buffer:
            buffer.write(file.file.read())

        return save_path

    def cleanup_old_uploads(self):
        """Deletes files older than CLEANUP_AGE_SECONDS."""
        now = time.time()
        cleaned = 0
        try:
            for filepath in UPLOAD_DIR.glob("*"):
                if filepath.is_file():
                    age = now - filepath.stat().st_mtime
                    if age > CLEANUP_AGE_SECONDS:
                        filepath.unlink()
                        cleaned += 1
            if cleaned > 0:
                logger.info(f"Cleaned up {cleaned} old upload files.")
        except Exception as e:
            logger.error(f"Failed to cleanup uploads: {e}")

upload_service = UploadService()
