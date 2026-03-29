import logging
from pathlib import Path
from typing import Tuple, Optional

from faster_whisper import WhisperModel

from ..config import settings

logger = logging.getLogger(__name__)

# Load the Whisper model once at module import time for efficiency.
logger.info("Loading faster-whisper model '%s'...", settings.WHISPER_MODEL_SIZE)
_whisper_model = WhisperModel(
    model_size_or_path=settings.WHISPER_MODEL_SIZE,
    device="cpu",  # change to "cuda" if you have a compatible GPU
    compute_type="int8",  # good trade-off on most CPUs
)
logger.info("Whisper model loaded successfully.")


def transcribe_audio(audio_path: Path) -> Tuple[str, Optional[str], Optional[float]]:
    """
    Transcribe an audio file using faster-whisper.

    Returns:
        transcript_text: full transcript as a single string
        language: detected language code (e.g. "en")
        duration_seconds: approximate duration in seconds
    """
    logger.info("Transcribing audio file at '%s'...", audio_path)

    segments, info = _whisper_model.transcribe(
        str(audio_path),
        beam_size=5,
        best_of=5,
    )

    transcript_parts: list[str] = []
    for segment in segments:
        transcript_parts.append(segment.text.strip())

    transcript_text = " ".join(transcript_parts).strip()
    language = getattr(info, "language", None)
    duration = getattr(info, "duration", None)

    logger.info(
        "Transcription complete: language=%s, duration=%.2f seconds",
        language,
        duration or 0.0,
    )

    return transcript_text, language, duration

