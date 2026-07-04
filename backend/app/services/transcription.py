"""
Transcription Service — wraps OpenAI Whisper API.

For MVP we use the openai whisper-1 model, which handles Indian languages
reasonably well as a general-purpose ASR model.
NOTE: This is NOT a fine-tuned vernacular model — that is the long-term vision.
The UI makes this distinction clear to the user.
"""
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Language code mapping for Whisper
LANGUAGE_MAP = {
    "hi": "hi",   # Hindi
    "ta": "ta",   # Tamil
    "te": "te",   # Telugu
    "mr": "mr",   # Marathi
    "gu": "gu",   # Gujarati
    "bn": "bn",   # Bengali
    "en": "en",   # English
}


class TranscriptionService:
    """Service for audio transcription via OpenAI Whisper"""

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY not set. Add it to backend/.env to enable transcription."
            )
        self.client = OpenAI(api_key=api_key)

    def transcribe(self, file_path: str, language: str = "en") -> str:
        """
        Transcribe an audio file using OpenAI Whisper.

        Args:
            file_path: Path to the audio file on disk
            language: ISO 639-1 language code (hi, ta, te, mr, gu, bn, en)

        Returns:
            Transcribed text string
        """
        whisper_lang = LANGUAGE_MAP.get(language, language)

        with open(file_path, "rb") as audio_file:
            response = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=whisper_lang,
                response_format="text"
            )

        return response
