#!/usr/bin/env python
"""
Data retention cleanup script (DPDP Act compliance).

Deletes raw call recording files (disk/S3) for recordings older than
each org's configured retention period (organizations.recording_retention_days).
The transcript and analysis_json columns are preserved — only the raw audio
file is deleted.

Run this on a schedule (e.g. daily cron / Railway scheduled job):
    python -m scripts.retention_cleanup

Or directly from the backend directory:
    python scripts/retention_cleanup.py
"""
import sys
import os
import logging
from datetime import datetime, timedelta

# Ensure the backend package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def run_cleanup():
    from app.db import SessionLocal
    from app.models import CallRecording, Organization
    from app.services.file_storage import delete_audio_file

    db = SessionLocal()
    try:
        orgs = db.query(Organization).all()
        total_deleted = 0

        for org in orgs:
            cutoff = datetime.utcnow() - timedelta(days=org.recording_retention_days)
            old_recordings = (
                db.query(CallRecording)
                .filter(
                    CallRecording.org_id == org.id,
                    CallRecording.created_at < cutoff,
                    # Only delete if there's actually a file (not already cleaned up)
                    CallRecording.file_path.isnot(None),
                )
                .all()
            )

            for rec in old_recordings:
                try:
                    delete_audio_file(rec.file_path, rec.storage_type)
                    # Null out the file_path to mark as cleaned up
                    rec.file_path = None
                    rec.storage_type = "deleted"
                    total_deleted += 1
                    log.info(f"Deleted recording file for org={org.id} recording={rec.id}")
                except Exception as e:
                    log.warning(f"Failed to delete recording {rec.id}: {e}")

        db.commit()
        log.info(f"Retention cleanup complete. Deleted {total_deleted} file(s).")
    finally:
        db.close()


if __name__ == "__main__":
    run_cleanup()
