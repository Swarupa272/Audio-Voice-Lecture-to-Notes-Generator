from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from .models import LectureStatus


class SectionSummary(BaseModel):
    """Summary for a specific section/chunk of a lecture."""

    section_title: Optional[str] = None
    summary: str
    chunk_id: Optional[str] = None


class Flashcard(BaseModel):
    """Flashcard generated from lecture content."""

    question: str
    answer: str
    difficulty: Optional[str] = "medium"


class LectureCreate(BaseModel):
    """Payload for creating a new lecture with an uploaded audio file."""

    title: str
    course: Optional[str] = None
    lecturer: Optional[str] = None
    lecture_date: Optional[str] = None  # ISO date string for simplicity


class LectureSummary(BaseModel):
    """Lightweight view for listing lectures."""

    id: str
    title: str
    course: Optional[str]
    lecturer: Optional[str]
    lecture_date: Optional[str]
    owner_email: str
    status: LectureStatus
    created_at: datetime
    updated_at: datetime


class LectureDetail(LectureSummary):
    """Detailed view for a single lecture."""

    audio_file_path: str
    transcript_text: Optional[str] = None
    transcript_language: Optional[str] = None
    duration_seconds: Optional[float] = None
    notes_text: Optional[str] = None
    error_message: Optional[str] = None
    section_summaries: Optional[list[SectionSummary]] = None
    flashcards: Optional[list[Flashcard]] = None


class NotesGenerationResponse(BaseModel):
    """Response returned after generating notes with the LLM."""

    notes_text: str
    status: LectureStatus = Field(default=LectureStatus.COMPLETED)


class QueryRequest(BaseModel):
    """Request body for querying notes with natural language."""

    query: str
    top_k: int = 4
    force_refresh: bool = False


class QueryResponse(BaseModel):
    """RAG answer and sources."""

    answer: str
    sources: list[str]


class SectionSummariesResponse(BaseModel):
    """List of summaries for lecture sections."""

    summaries: list[SectionSummary]


class FlashcardsResponse(BaseModel):
    """List of generated flashcards."""

    flashcards: list[Flashcard]

