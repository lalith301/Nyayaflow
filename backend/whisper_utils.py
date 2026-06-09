"""
NyayaFlow - Whisper Transcription Utility
Supports two modes via .env:
  DEPLOY_MODE=local      → faster-whisper running locally on CPU
  DEPLOY_MODE=production → Groq Whisper API (free tier, same API key)

Exposes:
    transcribe_audio(file_path: str) -> dict
    transcribe_audio_bytes(audio_bytes: bytes, ext: str) -> dict
"""

import os
import tempfile
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DEPLOY_MODE    = os.getenv("DEPLOY_MODE", "local")
WHISPER_MODEL  = "base"
SUPPORTED_EXTS = {".wav", ".mp3", ".m4a", ".webm", ".ogg", ".flac", ".mp4"}
INITIAL_PROMPT = (
    "This is a legal query in Indian English, Hindi, or Hinglish. "
    "The speaker may be asking about consumer rights, rental agreements, "
    "business contracts, or government schemes."
)

print(f"[whisper] Mode: {DEPLOY_MODE.upper()}")


# ─── Local mode: faster-whisper ───────────────────────────────────────────────

_local_model = None

def _get_local_model():
    global _local_model
    if _local_model is None:
        from faster_whisper import WhisperModel
        print(f"[whisper] Loading faster-whisper '{WHISPER_MODEL}' model…")
        _local_model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
        print("[whisper] Model loaded.")
    return _local_model


def _transcribe_local(file_path: str) -> dict:
    model = _get_local_model()

    # Convert to WAV if needed
    ext = Path(file_path).suffix.lower()
    wav_path = file_path
    if ext != ".wav":
        try:
            from pydub import AudioSegment
            audio    = AudioSegment.from_file(file_path)
            audio    = audio.set_frame_rate(16000).set_channels(1)
            wav_path = file_path.replace(ext, "_converted.wav")
            audio.export(wav_path, format="wav")
        except Exception as e:
            print(f"[whisper] Conversion failed ({e}), trying original.")

    segments, info = _get_local_model().transcribe(
        wav_path,
        initial_prompt=INITIAL_PROMPT,
        language=None,
        beam_size=5,
    )
    text = " ".join(seg.text.strip() for seg in segments)

    if wav_path != file_path and os.path.exists(wav_path):
        os.remove(wav_path)

    return {"text": text.strip(), "language": info.language}


# ─── Production mode: Groq Whisper API ───────────────────────────────────────

def _transcribe_groq(file_path: str) -> dict:
    """Use Groq's Whisper API — same API key, no local model needed."""
    from groq import Groq

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set in .env")

    client = Groq(api_key=api_key)

    with open(file_path, "rb") as f:
        transcription = client.audio.transcriptions.create(
            file=(Path(file_path).name, f.read()),
            model="whisper-large-v3",        # best model, free on Groq
            prompt=INITIAL_PROMPT,
            response_format="verbose_json",
            language=None,                   # auto-detect Hindi/English/Hinglish
        )

    return {
        "text":     transcription.text.strip(),
        "language": getattr(transcription, "language", "unknown"),
    }


# ─── Public interface ─────────────────────────────────────────────────────────

def transcribe_audio(file_path: str) -> dict:
    ext = Path(file_path).suffix.lower()
    if ext not in SUPPORTED_EXTS:
        return {"error": f"Unsupported audio format: {ext}. Supported: {SUPPORTED_EXTS}"}

    if DEPLOY_MODE == "production":
        return _transcribe_groq(file_path)
    return _transcribe_local(file_path)


def transcribe_audio_bytes(audio_bytes: bytes, ext: str = ".wav") -> dict:
    if not ext.startswith("."):
        ext = f".{ext}"
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name
    try:
        result = transcribe_audio(tmp_path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
    return result


# ─── CLI test ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys, json
    if len(sys.argv) < 2:
        print("Usage: python whisper_utils.py path/to/audio.wav")
        sys.exit(1)
    print(json.dumps(transcribe_audio(sys.argv[1]), indent=2, ensure_ascii=False))
