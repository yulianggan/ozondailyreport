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


def get_db(db_name: str = "ozondatas") -> AsyncIOMotorDatabase:
    return get_mongo_client()[db_name]


def get_collection(
    db_name: str = "ozondatas", collection_name: str = "operation_report"
) -> AsyncIOMotorCollection:
    return get_db(db_name)[collection_name]

