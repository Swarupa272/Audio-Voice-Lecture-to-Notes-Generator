import logging
from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorCollection

from .. import db
from ..config import settings
from ..models import LectureStatus
from ..schemas import (
    FlashcardsResponse,
    LectureCreate,
    LectureDetail,
    LectureSummary,
    NotesGenerationResponse,
    QueryRequest,
    QueryResponse,
    SectionSummariesResponse,
)
from ..services import rag
from ..services.export_service import export_notes_as_pdf, export_notes_as_text
from ..services.notes_generator import generate_notes_with_groq
from ..services.transcription import transcribe_audio

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/lectures", tags=["lectures"])


def get_lectures_collection_dep() -> AsyncIOMotorCollection:
    return db.get_lectures_collection()


def get_current_user_email(request: Request) -> str:
    email = request.session.get("user")
    if not email:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return str(email)


async def ensure_embeddings(doc: dict, lectures_col: AsyncIOMotorCollection) -> list[dict]:
    """Ensure embedding chunks exist for the lecture; create and persist if missing."""

    chunks = doc.get("embedding_chunks") or []
    if chunks:
        return chunks

    base_text = doc.get("notes_text") or doc.get("transcript_text")
    if not base_text:
        raise HTTPException(status_code=400, detail="No notes or transcript available to build embeddings.")

    embedding_chunks = rag.build_embedding_chunks(base_text)
    await lectures_col.update_one(
        {"_id": doc["_id"]},
        {"$set": {"embedding_chunks": embedding_chunks, "updated_at": datetime.utcnow()}},
    )
    return embedding_chunks


@router.post(
    "",
    response_model=LectureDetail,
    summary="Upload a new lecture audio file and trigger transcription.",
)
async def create_lecture(
    title: str = Form(...),
    course: str | None = Form(None),
    lecturer: str | None = Form(None),
    lecture_date: str | None = Form(None),
    audio_file: UploadFile = File(...),
    current_user_email: str = Depends(get_current_user_email),
    lectures_col: AsyncIOMotorCollection = Depends(get_lectures_collection_dep),
):
    # 1. Store initial lecture document
    now = datetime.utcnow()
    lecture_doc = {
        "title": title,
        "course": course,
        "lecturer": lecturer,
        "lecture_date": lecture_date,
        "audio_file_path": "",
        "transcript_text": None,
        "transcript_language": None,
        "duration_seconds": None,
        "notes_text": None,
        "status": LectureStatus.TRANSCRIBING.value,
        "created_at": now,
        "updated_at": now,
        "error_message": None,
        "owner_email": current_user_email,
    }

    result = await lectures_col.insert_one(lecture_doc)
    lecture_id = result.inserted_id

    # 2. Save audio file to disk
    file_extension = Path(audio_file.filename or "").suffix or ".webm"
    audio_path = settings.AUDIO_DIR / f"{lecture_id}{file_extension}"

    try:
        with audio_path.open("wb") as f:
            f.write(await audio_file.read())
    except Exception as exc:
        logger.exception("Failed to save uploaded audio: %s", exc)
        await lectures_col.update_one(
            {"_id": lecture_id},
            {
                "$set": {
                    "status": LectureStatus.ERROR.value,
                    "error_message": f"Failed to save audio: {exc}",
                    "updated_at": datetime.utcnow(),
                }
            },
        )
        raise HTTPException(status_code=500, detail="Failed to save audio file.")

    await lectures_col.update_one(
        {"_id": lecture_id},
        {
            "$set": {
                "audio_file_path": str(audio_path),
                "updated_at": datetime.utcnow(),
            }
        },
    )

    # 3. Run transcription synchronously (simpler for project)
    try:
        transcript_text, language, duration = transcribe_audio(audio_path)
        await lectures_col.update_one(
            {"_id": lecture_id},
            {
                "$set": {
                    "transcript_text": transcript_text,
                    "transcript_language": language,
                    "duration_seconds": duration,
                    "status": LectureStatus.TRANSCRIBED.value,
                    "updated_at": datetime.utcnow(),
                }
            },
        )
    except Exception as exc:
        logger.exception("Transcription failed: %s", exc)
        await lectures_col.update_one(
            {"_id": lecture_id},
            {
                "$set": {
                    "status": LectureStatus.ERROR.value,
                    "error_message": f"Transcription failed: {exc}",
                    "updated_at": datetime.utcnow(),
                }
            },
        )
        raise HTTPException(status_code=500, detail="Transcription failed.")

    # 4. Return newly created lecture
    doc = await lectures_col.find_one({"_id": lecture_id})
    if not doc:
        raise HTTPException(status_code=500, detail="Lecture not found after creation.")

    return LectureDetail(**db.lecture_to_dict(doc))


@router.get(
    "",
    response_model=List[LectureSummary],
    summary="List all lectures with basic information.",
)
async def list_lectures(
    current_user_email: str = Depends(get_current_user_email),
    lectures_col: AsyncIOMotorCollection = Depends(get_lectures_collection_dep),
):
    cursor = (
        lectures_col.find({"owner_email": current_user_email}).sort("created_at", -1)
    )
    lectures: list[LectureSummary] = []
    async for doc in cursor:
        lectures.append(
            LectureSummary(
                **db.lecture_to_dict(doc),
            )
        )
    return lectures


@router.get(
    "/{lecture_id}",
    response_model=LectureDetail,
    summary="Get full details for a specific lecture.",
)
async def get_lecture(
    lecture_id: str,
    current_user_email: str = Depends(get_current_user_email),
    lectures_col: AsyncIOMotorCollection = Depends(get_lectures_collection_dep),
):
    try:
        oid = db.object_id(lecture_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid lecture id.")

    doc = await lectures_col.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Lecture not found.")
    if doc.get("owner_email") != current_user_email:
        raise HTTPException(status_code=403, detail="Access denied")

    return LectureDetail(**db.lecture_to_dict(doc))


@router.post(
    "/{lecture_id}/generate-notes",
    response_model=NotesGenerationResponse,
    summary="Generate AI-powered lecture notes using local LLM.",
)
async def generate_notes(
    lecture_id: str,
    current_user_email: str = Depends(get_current_user_email),
    lectures_col: AsyncIOMotorCollection = Depends(get_lectures_collection_dep),
):
    try:
        oid = db.object_id(lecture_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid lecture id.")

    doc = await lectures_col.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Lecture not found.")
    if doc.get("owner_email") != current_user_email:
        raise HTTPException(status_code=403, detail="Access denied")

    if not doc.get("transcript_text"):
        raise HTTPException(status_code=400, detail="Transcript not available.")

    await lectures_col.update_one(
        {"_id": oid},
        {
            "$set": {
                "status": LectureStatus.GENERATING_NOTES.value,
                "updated_at": datetime.utcnow(),
            }
        },
    )

    try:
        notes_text = generate_notes_with_groq(
            transcript=doc["transcript_text"],
            title=doc.get("title", ""),
            course=doc.get("course"),
            lecturer=doc.get("lecturer"),
            lecture_date=doc.get("lecture_date"),
        )

        await lectures_col.update_one(
            {"_id": oid},
            {
                "$set": {
                    "notes_text": notes_text,
                    "status": LectureStatus.COMPLETED.value,
                    "updated_at": datetime.utcnow(),
                }
            },
        )

        # Build embeddings for later RAG queries (best effort)
        try:
            embedding_chunks = rag.build_embedding_chunks(notes_text)
            await lectures_col.update_one(
                {"_id": oid},
                {
                    "$set": {
                        "embedding_chunks": embedding_chunks,
                        "updated_at": datetime.utcnow(),
                    }
                },
            )
        except Exception as exc:
            logger.warning("Embedding build failed (continuing): %s", exc)

        return NotesGenerationResponse(notes_text=notes_text)
    except Exception as exc:
        await lectures_col.update_one(
            {"_id": oid},
            {
                "$set": {
                    "status": LectureStatus.ERROR.value,
                    "error_message": f"Notes generation failed: {exc}",
                    "updated_at": datetime.utcnow(),
                }
            },
        )
        raise HTTPException(status_code=500, detail="Notes generation failed.")


@router.post(
    "/{lecture_id}/query",
    response_model=QueryResponse,
    summary="Query notes with natural language using RAG.",
)
async def query_notes(
    lecture_id: str,
    payload: QueryRequest,
    current_user_email: str = Depends(get_current_user_email),
    lectures_col: AsyncIOMotorCollection = Depends(get_lectures_collection_dep),
):
    try:
        oid = db.object_id(lecture_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid lecture id.")

    doc = await lectures_col.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Lecture not found.")
    if doc.get("owner_email") != current_user_email:
        raise HTTPException(status_code=403, detail="Access denied")

    if payload.force_refresh:
        await lectures_col.update_one(
            {"_id": oid},
            {"$unset": {"embedding_chunks": ""}},
        )
        doc.pop("embedding_chunks", None)

    chunks = await ensure_embeddings(doc, lectures_col)
    scored = rag.retrieve(payload.query, chunks, payload.top_k)
    answer_payload = rag.answer_question(payload.query, scored)
    return QueryResponse(**answer_payload)


@router.post(
    "/{lecture_id}/summaries/sections",
    response_model=SectionSummariesResponse,
    summary="Generate section-level summaries for a lecture.",
)
async def summarize_sections(
    lecture_id: str,
    force: bool = False,
    current_user_email: str = Depends(get_current_user_email),
    lectures_col: AsyncIOMotorCollection = Depends(get_lectures_collection_dep),
):
    try:
        oid = db.object_id(lecture_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid lecture id.")

    doc = await lectures_col.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Lecture not found.")
    if doc.get("owner_email") != current_user_email:
        raise HTTPException(status_code=403, detail="Access denied")

    if doc.get("section_summaries") and not force:
        return SectionSummariesResponse(summaries=doc["section_summaries"])

    base_text = doc.get("notes_text") or doc.get("transcript_text")
    if not base_text:
        raise HTTPException(status_code=400, detail="Notes or transcript required for summaries.")

    source_chunks = doc.get("embedding_chunks") or []
    if not source_chunks:
        raw_chunks = rag.chunk_text(base_text)
        source_chunks = [
            {"id": str(i), "text": text, "section_title": None} for i, text in enumerate(raw_chunks)
        ]

    summaries = []
    for chunk in source_chunks:
        text = chunk.get("text") or ""
        if not text.strip():
            continue
        summary_text = rag.summarize_section(chunk.get("section_title") or "", text)
        summaries.append(
            {
                "section_title": chunk.get("section_title"),
                "summary": summary_text,
                "chunk_id": chunk.get("id"),
            }
        )

    await lectures_col.update_one(
        {"_id": oid},
        {
            "$set": {
                "section_summaries": summaries,
                "updated_at": datetime.utcnow(),
            }
        },
    )

    return SectionSummariesResponse(summaries=summaries)


@router.post(
    "/{lecture_id}/flashcards",
    response_model=FlashcardsResponse,
    summary="Generate flashcards from lecture content.",
)
async def create_flashcards(
    lecture_id: str,
    count: int = 8,
    current_user_email: str = Depends(get_current_user_email),
    lectures_col: AsyncIOMotorCollection = Depends(get_lectures_collection_dep),
):
    try:
        oid = db.object_id(lecture_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid lecture id.")

    doc = await lectures_col.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Lecture not found.")
    if doc.get("owner_email") != current_user_email:
        raise HTTPException(status_code=403, detail="Access denied")

    base_text = doc.get("notes_text") or doc.get("transcript_text")
    if not base_text:
        raise HTTPException(status_code=400, detail="Notes or transcript required for flashcards.")

    cards = rag.generate_flashcards(base_text, count=count)

    await lectures_col.update_one(
        {"_id": oid},
        {"$set": {"flashcards": cards, "updated_at": datetime.utcnow()}},
    )

    return FlashcardsResponse(flashcards=cards)

@router.delete(
    "/{lecture_id}",
    summary="Delete a lecture and its associated files.",
)
async def delete_lecture(
    lecture_id: str,
    current_user_email: str = Depends(get_current_user_email),
    lectures_col: AsyncIOMotorCollection = Depends(get_lectures_collection_dep),
):
    try:
        oid = db.object_id(lecture_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid lecture id.")

    doc = await lectures_col.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Lecture not found.")
    if doc.get("owner_email") != current_user_email:
        raise HTTPException(status_code=403, detail="Access denied")

    # Delete audio file if it exists
    audio_path = doc.get("audio_file_path")
    if audio_path:
        try:
            audio_file = Path(audio_path)
            if audio_file.exists():
                audio_file.unlink()
                logger.info("Deleted audio file: %s", audio_path)
        except Exception as e:
            logger.warning("Failed to delete audio file %s: %s", audio_path, e)

    # Delete from database
    result = await lectures_col.delete_one({"_id": oid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=500, detail="Failed to delete lecture.")

    logger.info("Lecture deleted: %s", lecture_id)
    return {"message": "Lecture deleted successfully", "id": lecture_id}


@router.get(
    "/{lecture_id}/export",
    summary="Export notes for a lecture as PDF or plain text.",
)
async def export_notes(
    lecture_id: str,
    format: str = "pdf",
    current_user_email: str = Depends(get_current_user_email),
    lectures_col: AsyncIOMotorCollection = Depends(get_lectures_collection_dep),
):
    try:
        oid = db.object_id(lecture_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid lecture id.")

    doc = await lectures_col.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Lecture not found.")
    if doc.get("owner_email") != current_user_email:
        raise HTTPException(status_code=403, detail="Access denied")

    if not doc.get("notes_text"):
        raise HTTPException(status_code=400, detail="Notes not available.")

    title = doc.get("title", "Lecture Notes")
    notes_text = doc["notes_text"]

    if format == "txt":
        file_bytes, filename = export_notes_as_text(title, notes_text)
        media_type = "text/plain"
    elif format == "pdf":
        file_bytes, filename = export_notes_as_pdf(title, notes_text)
        media_type = "application/pdf"
    else:
        raise HTTPException(status_code=400, detail="Unsupported export format.")

    return StreamingResponse(
        iter([file_bytes]),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

