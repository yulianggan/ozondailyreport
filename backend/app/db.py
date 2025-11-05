import os
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection


_client: Optional[AsyncIOMotorClient] = None


def get_mongo_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        _client = AsyncIOMotorClient(uri)
    return _client


def get_db(db_name: str | None = None) -> AsyncIOMotorDatabase:
    if db_name is None:
        db_name = os.getenv("MONGODB_DB", "ozondatas")
    return get_mongo_client()[db_name]


def get_collection(
    db_name: str | None = None, collection_name: str | None = None
) -> AsyncIOMotorCollection:
    if db_name is None:
        db_name = os.getenv("MONGODB_DB", "ozondatas")
    if collection_name is None:
        collection_name = os.getenv("MONGODB_COLL", os.getenv("MONGODB_COLLECTION", "operation_report"))
    return get_db(db_name)[collection_name]
