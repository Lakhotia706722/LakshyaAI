from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db import get_db
from app.models import CallRecording, Deal
from app.schemas import CallRecordingResponse
from app.routers.auth import get_current_user_with_org
from app.services.ai_extraction import AIExtractionService
from app.services.transcription import TranscriptionService
from app.services.file_storage import (
    validate_audio_upload,
    save_audio_file,
    delete_audio_file,
    audio_file_for_transcription,
)
import os

router = APIRouter()

ALLOWED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".webm"}


@router.post("/upload", response_model=CallRecordingResponse)
async def upload_call_recording(
    file: UploadFile = File(...),
    language: str = Form("en"),
    deal_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    user_org_role: tuple = Depends(get_current_user_with_org),
):
    """
    Upload an audio file for transcription and analysis.
    Supports Hindi, Tamil, Telugu, Marathi, Gujarati, Bengali, English.
    """
    user, org_id, _ = user_org_role

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Read file bytes for validation + storage
    file_bytes = await file.read()

    # Validate via magic bytes and size
    try:
        validate_audio_upload(file_bytes, file.filename)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    # Verify deal belongs to this org if provided
    if deal_id:
        deal = db.query(Deal).filter(Deal.id == deal_id, Deal.org_id == org_id).first()
        if not deal:
            raise HTTPException(status_code=404, detail="Deal not found")

    # Save file
    try:
        file_path, storage_type = save_audio_file(file_bytes, user.id, ext)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # Transcribe
    transcript = None
    analysis = None

    try:
        transcription_service = TranscriptionService()
        with audio_file_for_transcription(file_path, storage_type) as local_path:
            transcript = transcription_service.transcribe(local_path, language)
    except ValueError as e:
        analysis = {
            "error": str(e),
            "talk_time_ratio": None,
            "objections": [],
            "competitor_mentions": [],
            "coaching_notes": ["AI service not configured — add OPENAI_API_KEY to enable transcription."],
        }
    except Exception as e:
        analysis = {
            "error": f"Transcription failed: {str(e)}",
            "talk_time_ratio": None,
            "objections": [],
            "competitor_mentions": [],
            "coaching_notes": [],
        }

    # Analyze if we have a transcript
    if transcript and analysis is None:
        try:
            ai_service = AIExtractionService()
            analysis = ai_service.analyze_call_transcript(transcript, language)
        except Exception as e:
            analysis = {
                "error": f"Analysis failed: {str(e)}",
                "talk_time_ratio": None,
                "objections": [],
                "competitor_mentions": [],
                "coaching_notes": [],
            }

    recording = CallRecording(
        org_id=org_id,
        deal_id=deal_id,
        file_path=file_path,
        storage_type=storage_type,
        language=language,
        transcript=transcript,
        analysis_json=analysis,
    )
    db.add(recording)
    db.commit()
    db.refresh(recording)
    return recording


@router.get("/", response_model=List[CallRecordingResponse])
def get_recordings(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    user_org_role: tuple = Depends(get_current_user_with_org),
):
    """Get all call recordings for the current org."""
    _, org_id, _ = user_org_role
    return (
        db.query(CallRecording)
        .filter(CallRecording.org_id == org_id)
        .order_by(CallRecording.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/{recording_id}", response_model=CallRecordingResponse)
def get_recording(
    recording_id: int,
    db: Session = Depends(get_db),
    user_org_role: tuple = Depends(get_current_user_with_org),
):
    """Get a specific call recording (org-scoped)."""
    _, org_id, _ = user_org_role
    recording = db.query(CallRecording).filter(
        CallRecording.id == recording_id, CallRecording.org_id == org_id
    ).first()
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    return recording
