from pathlib import Path

from pydantic import ValidationError
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration loaded from environment variables or defaults."""

    # MongoDB
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "lecture_notes_db"

    # Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATA_DIR: Path = BASE_DIR.parent.parent / "data"
    AUDIO_DIR: Path = DATA_DIR / "audio"
    EXPORTS_DIR: Path = DATA_DIR / "exports"
    USERS_DIR: Path = DATA_DIR / "users"

    # Auth / sessions
    SESSION_SECRET: str = "change-this-secret"

    # Whisper model
    WHISPER_MODEL_SIZE: str = "small"  # "tiny", "base", "small", "medium", etc.

    # Groq
    GROQ_API_KEY: str
    GROQ_MODEL_NAME: str = "llama-3.3-70b-versatile"

    # OpenAI embeddings (for RAG)
    OPENAI_API_KEY: str
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


try:
    settings = Settings()
except ValidationError as exc:
    missing_fields: list[str] = []
    for error in exc.errors():
        location = error.get("loc", ())
        if location:
            missing_fields.append(str(location[0]))

    fields_display = ", ".join(sorted(set(missing_fields))) or "required settings"
    raise RuntimeError(
        "Missing required environment configuration. "
        "Create a .env file in the project root (you can copy .env.example) "
        f"and set: {fields_display}."
    ) from exc

# Ensure required directories exist
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.AUDIO_DIR.mkdir(parents=True, exist_ok=True)
settings.EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
settings.USERS_DIR.mkdir(parents=True, exist_ok=True)