from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import shutil

from app.db import get_db
from app.models import CallRecording, Deal, User
from app.schemas import CallRecordingResponse
from app.routers.auth import get_current_user
from app.services.ai_extraction import AIExtractionService
from app.services.transcription import TranscriptionService

router = APIRouter()

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
ALLOWED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".webm"}


@router.post("/upload", response_model=CallRecordingResponse)
async def upload_call_recording(
    file: UploadFile = File(...),
    language: str = Form("en"),
    deal_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload an audio file for transcription and analysis.
    Supports Hindi, Tamil, Telugu, Marathi, Gujarati, Bengali, English.
    """
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Validate deal exists if provided
    if deal_id:
        deal = db.query(Deal).filter(Deal.id == deal_id).first()
        if not deal:
            raise HTTPException(status_code=404, detail="Deal not found")

    # Save file to uploads directory
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    safe_filename = f"call_{current_user.id}_{int(__import__('time').time())}{ext}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # Transcribe
    try:
        transcription_service = TranscriptionService()
        transcript = transcription_service.transcribe(file_path, language)
    except ValueError as e:
        # API key not configured — save record without transcript
        transcript = None
        analysis = {
            "error": str(e),
            "talk_time_ratio": None,
            "objections": [],
            "competitor_mentions": [],
            "coaching_notes": ["AI service not configured — add OPENAI_API_KEY to enable transcription."]
        }
    except Exception as e:
        transcript = None
        analysis = {
            "error": f"Transcription failed: {str(e)}",
            "talk_time_ratio": None,
            "objections": [],
            "competitor_mentions": [],
            "coaching_notes": []
        }
    else:
        # Analyze transcript with Claude
        try:
            ai_service = AIExtractionService()
            analysis = ai_service.analyze_call_transcript(transcript, language)
        except Exception as e:
            analysis = {
                "error": f"Analysis failed: {str(e)}",
                "talk_time_ratio": None,
                "objections": [],
                "competitor_mentions": [],
                "coaching_notes": []
            }

    # Save to DB
    recording = CallRecording(
        deal_id=deal_id,
        file_path=file_path,
        language=language,
        transcript=transcript,
        analysis_json=analysis
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
    current_user: User = Depends(get_current_user)
):
    """Get all call recordings"""
    return db.query(CallRecording).order_by(
        CallRecording.created_at.desc()
    ).offset(skip).limit(limit).all()


@router.get("/{recording_id}", response_model=CallRecordingResponse)
def get_recording(
    recording_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific call recording"""
    recording = db.query(CallRecording).filter(CallRecording.id == recording_id).first()
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    return recording
