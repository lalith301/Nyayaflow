"""
NyayaFlow - Whisper transcription
Uses Groq Whisper API (whisper-large-v3) — works in both local and production.
No FFmpeg or faster-whisper needed.
"""

import os
import tempfile
from groq import Groq

def transcribe_audio_bytes(audio_bytes: bytes, ext: str = ".webm") -> dict:
    """
    Transcribe audio using Groq Whisper API.
    Supports Hindi, English, Hinglish automatically.
    """
    try:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))

        # Write to temp file — Groq needs a file object
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        with open(tmp_path, "rb") as f:
            result = client.audio.transcriptions.create(
                file=(f"recording{ext}", f),
                model="whisper-large-v3",
                response_format="json",
            )

        os.unlink(tmp_path)

        return {
            "text":     result.text.strip(),
            "language": getattr(result, "language", "auto"),
        }

    except Exception as e:
        print(f"[whisper] Groq transcription error: {e}")
        return {"error": str(e)}