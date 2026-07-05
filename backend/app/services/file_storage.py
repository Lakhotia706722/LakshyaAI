"""
File storage service.

Stores uploaded audio files in S3 when configured, falls back to local
filesystem for local development.

The Whisper transcription service downloads the file from S3 to a temp
file before passing it to the API (simple, reliable, works with existing
TranscriptionService interface).
"""
from __future__ import annotations

import logging
import os
import tempfile
import time
from contextlib import contextmanager
from typing import Tuple

from app.config import get_settings

settings = get_settings()
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# MIME type validation (magic bytes, not Content-Type header)
# ─────────────────────────────────────────────────────────────

# Audio magic byte signatures
_AUDIO_MAGIC: list[tuple[bytes, str]] = [
    (b"\xff\xfb", "mp3"),
    (b"\xff\xf3", "mp3"),
    (b"\xff\xf2", "mp3"),
    (b"ID3", "mp3"),
    (b"RIFF", "wav"),   # WAV: RIFF....WAVE
    (b"OggS", "ogg"),
    (b"\x1a\x45\xdf\xa3", "webm"),  # WebM / MKV
    (b"fLaC", "flac"),
]

# M4A is MP4 container — check for ftyp box
_MP4_SIGNATURES = [b"ftyp", b"moov", b"mdat"]


def _is_audio_bytes(header: bytes) -> bool:
    """Check the first 16 bytes of a file for known audio signatures."""
    for sig, _ in _AUDIO_MAGIC:
        if header.startswith(sig):
            return True
    # M4A / MP4: ftyp box usually at offset 4
    if len(header) >= 8 and header[4:8] in _MP4_SIGNATURES:
        return True
    return False


MAX_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024


def validate_audio_upload(file_bytes: bytes, filename: str) -> None:
    """
    Validate uploaded audio file.
    Raises ValueError with a human-readable message on failure.
    """
    if len(file_bytes) > MAX_BYTES:
        raise ValueError(
            f"File too large ({len(file_bytes) // (1024*1024)} MB). "
            f"Maximum allowed: {settings.MAX_UPLOAD_SIZE_MB} MB."
        )
    if len(file_bytes) < 4:
        raise ValueError("File is empty or too small to be a valid audio file.")
    if not _is_audio_bytes(file_bytes[:16]):
        raise ValueError(
            "File does not appear to be a valid audio file. "
            "Only MP3, WAV, M4A, OGG, and WebM formats are accepted."
        )


# ─────────────────────────────────────────────────────────────
# Storage backends
# ─────────────────────────────────────────────────────────────

def _save_local(file_bytes: bytes, filename: str) -> Tuple[str, str]:
    """Save to local filesystem. Returns (file_path, storage_type)."""
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    path = os.path.join(settings.UPLOAD_DIR, filename)
    with open(path, "wb") as f:
        f.write(file_bytes)
    return path, "local"


def _save_s3(file_bytes: bytes, s3_key: str) -> Tuple[str, str]:
    """Upload to S3. Returns (s3_key, storage_type)."""
    import boto3
    s3 = boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )
    s3.put_object(
        Bucket=settings.AWS_S3_BUCKET,
        Key=s3_key,
        Body=file_bytes,
        ContentType="audio/mpeg",
    )
    return s3_key, "s3"


def save_audio_file(file_bytes: bytes, user_id: int, ext: str) -> Tuple[str, str]:
    """
    Save an audio file to S3 (if configured) or local filesystem.
    Returns (file_path_or_key, storage_type).
    """
    filename = f"call_{user_id}_{int(time.time())}{ext}"
    if settings.s3_enabled:
        s3_key = f"recordings/{filename}"
        return _save_s3(file_bytes, s3_key)
    return _save_local(file_bytes, filename)


def delete_audio_file(file_path: str, storage_type: str) -> None:
    """Delete an audio file from local disk or S3."""
    try:
        if storage_type == "s3" and settings.s3_enabled:
            import boto3
            s3 = boto3.client(
                "s3",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION,
            )
            s3.delete_object(Bucket=settings.AWS_S3_BUCKET, Key=file_path)
        elif storage_type == "local" and os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        log.warning(f"Failed to delete file {file_path}: {e}")


@contextmanager
def audio_file_for_transcription(file_path: str, storage_type: str):
    """
    Context manager that yields a local filesystem path suitable for passing
    to the Whisper API.

    For S3 files: downloads to a named temp file, yields the path, then cleans up.
    For local files: yields the path directly.
    """
    if storage_type == "s3":
        import boto3
        ext = os.path.splitext(file_path)[1] or ".mp3"
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp_path = tmp.name
        try:
            s3 = boto3.client(
                "s3",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION,
            )
            s3.download_file(settings.AWS_S3_BUCKET, file_path, tmp_path)
            yield tmp_path
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    else:
        yield file_path
