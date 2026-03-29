import logging
import math
import uuid
from typing import Dict, List, Optional, Tuple

from groq import Groq
from openai import OpenAI, RateLimitError

from ..config import settings

logger = logging.getLogger(__name__)

# When set, embedding calls are skipped to avoid repeated external errors/quota hits.
_embeddings_disabled = False


class EmbeddingError(RuntimeError):
    """Raised when embedding creation fails."""


class RAGConfig:
    """Configuration values for retrieval and prompts."""

    chunk_max_chars: int = 1400
    chunk_min_chars: int = 400
    top_k: int = 4
    min_score: float = 0.15


client_openai = OpenAI(api_key=settings.OPENAI_API_KEY)
client_groq = Groq(api_key=settings.GROQ_API_KEY)


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Pure-Python cosine similarity to avoid heavyweight deps."""

    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def chunk_text(text: str, max_chars: int | None = None, min_chars: int | None = None) -> List[str]:
    """Simple chunker that respects paragraphs and length limits."""

    if not text:
        return []

    max_len = max_chars or RAGConfig.chunk_max_chars
    min_len = min_chars or RAGConfig.chunk_min_chars

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: List[str] = []
    current: List[str] = []
    current_len = 0

    def flush():
        nonlocal current, current_len
        if current:
            combined = "\n".join(current).strip()
            if combined:
                chunks.append(combined)
        current = []
        current_len = 0

    for para in paragraphs:
        para_len = len(para)
        if para_len > max_len:
            # Break long paragraph into sentences-ish on periods.
            sentences = [s.strip() for s in para.replace("?", ".").split(".") if s.strip()]
            for sentence in sentences:
                if not sentence:
                    continue
                if current_len + len(sentence) + 1 > max_len:
                    flush()
                current.append(sentence)
                current_len += len(sentence) + 1
                if current_len >= min_len:
                    flush()
            flush()
            continue

        if current_len + para_len + 2 > max_len:
            flush()
        current.append(para)
        current_len += para_len + 2
        if current_len >= min_len:
            flush()

    flush()
    return chunks


def embed_texts(chunks: List[str]) -> List[List[float]]:
    """Create embeddings using OpenAI embeddings API."""

    global _embeddings_disabled

    if not chunks:
        return []
    if _embeddings_disabled:
        logger.info("Embeddings disabled; skipping request.")
        return []
    if not settings.OPENAI_API_KEY:
        logger.warning("Skipping embeddings: OPENAI_API_KEY is not set.")
        _embeddings_disabled = True
        return []
    try:
        response = client_openai.embeddings.create(
            model=settings.OPENAI_EMBEDDING_MODEL,
            input=chunks,
        )
        vectors: List[List[float]] = [item.embedding for item in response.data]
        return vectors
    except RateLimitError as exc:  # pragma: no cover - network path
        logger.warning("Skipping embeddings due to rate limit/quota: %s", exc)
        _embeddings_disabled = True
        return []
    except Exception as exc:  # pragma: no cover - network path
        logger.exception("Failed to create embeddings: %s", exc)
        raise EmbeddingError("Embedding generation failed") from exc


def build_embedding_chunks(text: str) -> List[Dict[str, object]]:
    """Chunk text and attach embeddings for each chunk."""

    raw_chunks = chunk_text(text)
    vectors = embed_texts(raw_chunks)
    if not vectors:
        return []
    embedding_chunks: List[Dict[str, object]] = []
    for chunk_text_val, vector in zip(raw_chunks, vectors):
        embedding_chunks.append(
            {
                "id": str(uuid.uuid4()),
                "text": chunk_text_val,
                "section_title": None,
                "vector": vector,
            }
        )
    return embedding_chunks


def retrieve(query: str, chunks: List[Dict[str, object]], top_k: int | None = None) -> List[Tuple[Dict[str, object], float]]:
    """Find top chunks by cosine similarity."""

    if not chunks:
        return []
    query_vecs = embed_texts([query])
    if not query_vecs:
        return []
    query_vec = query_vecs[0]
    scored: List[Tuple[Dict[str, object], float]] = []
    for chunk in chunks:
        vector = chunk.get("vector") or []
        score = _cosine_similarity(query_vec, vector)
        if score >= RAGConfig.min_score:
            scored.append((chunk, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[: top_k or RAGConfig.top_k]


def build_answer_prompt(question: str, contexts: List[Tuple[Dict[str, object], float]]) -> List[Dict[str, str]]:
    """Construct messages for Groq chat completion grounded to provided contexts."""

    context_blocks = []
    for idx, (chunk, score) in enumerate(contexts, start=1):
        context_blocks.append(f"{idx}) [score={score:.2f}] {chunk.get('section_title') or 'Section'}\n{chunk.get('text','')}")
    context_text = "\n\n".join(context_blocks)

    user_content = (
        "You are a concise study assistant. Answer ONLY using the provided context. "
        "If the context is insufficient, say you do not know.\n\n"
        f"Question: {question}\n\nContext:\n{context_text}\n\n"
        "Return:\n"
        "- A brief answer (2-5 sentences)\n"
        "- A bullet list of cited sections by their order numbers"
    )

    return [
        {"role": "system", "content": "You are a helpful, concise study assistant."},
        {"role": "user", "content": user_content},
    ]


def answer_question(question: str, contexts: List[Tuple[Dict[str, object], float]]) -> Dict[str, object]:
    """Call Groq chat to produce an answer grounded in contexts."""

    if not contexts:
        return {"answer": "I don't have enough information to answer.", "sources": []}

    messages = build_answer_prompt(question, contexts)

    try:
        response = client_groq.chat.completions.create(
            model=settings.GROQ_MODEL_NAME,
            messages=messages,
            temperature=0.2,
            max_tokens=400,
        )
        content = (response.choices[0].message.content or "").strip()
    except Exception as exc:  # pragma: no cover - network path
        logger.exception("Failed to generate answer via Groq: %s", exc)
        raise RuntimeError("Answer generation failed") from exc

    return {
        "answer": content,
        "sources": [ctx[0].get("section_title") or f"Chunk {i+1}" for i, ctx in enumerate(contexts)],
    }


def summarize_section(title: str, text: str) -> str:
    """Summarize a section of text with Groq."""

    prompt = (
        "Summarize the section into 3-5 bullet points. Use plain text bullets starting with '-'. "
        "Avoid markdown headings.\n"
        f"Section: {title or 'Untitled'}\n"
        f"Text:\n{text}"
    )
    try:
        response = client_groq.chat.completions.create(
            model=settings.GROQ_MODEL_NAME,
            messages=[
                {"role": "system", "content": "You create concise study bullet points."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=300,
        )
        return (response.choices[0].message.content or "").strip()
    except Exception as exc:  # pragma: no cover
        logger.exception("Failed to summarize section: %s", exc)
        raise RuntimeError("Section summary failed") from exc


def generate_flashcards(text: str, count: int = 8) -> List[Dict[str, str]]:
    """Generate flashcards (Q/A) from provided text."""

    prompt = (
        f"Create {count} flashcards from the context. Each card should have short question, short answer, "
        "and difficulty (easy|medium|hard). Return plain text bullet list in the form 'Q: ... | A: ... | Difficulty: ...'.\n"
        f"Context:\n{text}"
    )
    try:
        response = client_groq.chat.completions.create(
            model=settings.GROQ_MODEL_NAME,
            messages=[
                {"role": "system", "content": "You create brief flashcards."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=500,
        )
        raw = (response.choices[0].message.content or "").strip()
    except Exception as exc:  # pragma: no cover
        logger.exception("Failed to generate flashcards: %s", exc)
        raise RuntimeError("Flashcard generation failed") from exc

    cards: List[Dict[str, str]] = []
    for line in raw.splitlines():
        line = line.strip("- ").strip()
        if not line or "Q:" not in line or "A:" not in line:
            continue
        parts = [part.strip() for part in line.split("|")]
        q = next((p.replace("Q:", "").strip() for p in parts if p.lower().startswith("q:")), "")
        a = next((p.replace("A:", "").strip() for p in parts if p.lower().startswith("a:")), "")
        difficulty = next((p.replace("Difficulty:", "").strip() for p in parts if p.lower().startswith("difficulty")), "" )
        if q and a:
            cards.append({"question": q, "answer": a, "difficulty": difficulty or "medium"})
    return cards
