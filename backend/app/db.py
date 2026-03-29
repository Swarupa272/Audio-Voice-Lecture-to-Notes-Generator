from typing import Any, Dict

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection

from .config import settings

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    """Return a singleton MongoDB client."""

    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.MONGODB_URI)
    return _client


def get_database():
    """Get the application database."""

    return get_client()[settings.MONGODB_DB_NAME]


def get_lectures_collection() -> AsyncIOMotorCollection:
    """Get the lectures collection."""

    return get_database()["lectures"]


def get_users_collection() -> AsyncIOMotorCollection:
    """Get the users collection."""

    return get_database()["users"]


def lecture_to_dict(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a raw MongoDB lecture document to a JSON-serializable dict."""

    if not doc:
        return {}
    doc["id"] = str(doc.pop("_id"))
    return doc


def object_id(id_str: str) -> ObjectId:
    """Helper to convert string id to ObjectId."""

    return ObjectId(id_str)

