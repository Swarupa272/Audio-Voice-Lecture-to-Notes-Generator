from enum import Enum


class LectureStatus(str, Enum):
    """Possible processing states for a lecture."""

    UPLOADED = "UPLOADED"
    TRANSCRIBING = "TRANSCRIBING"
    TRANSCRIBED = "TRANSCRIBED"
    GENERATING_NOTES = "GENERATING_NOTES"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"

