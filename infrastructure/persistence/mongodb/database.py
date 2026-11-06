from typing import Optional
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection

from infrastructure.config.settings import settings


class MongoDBManager:
    """Manages the MongoDB client connection lifecycle."""

    def __init__(self, mongo_url: str = settings.MONGO_URL, db_name: str = settings.DATABASE_NAME):
        self._mongo_url = mongo_url
        self._db_name = db_name
        self._client: Optional[MongoClient] = None
        self._db: Optional[Database] = None

    def get_client(self) -> MongoClient:
        if self._client is None:
            self._client = MongoClient(self._mongo_url)
        return self._client

    def get_database(self) -> Database:
        if self._db is None:
            client = self.get_client()
            self._db = client[self._db_name]
        return self._db

    def get_collection(self, collection_name: str = settings.TODO_COLLECTION_NAME) -> Collection:
        return self.get_database()[collection_name]

    def connect(self) -> None:
        """Pings the database to verify the connection is active."""
        try:
            client = self.get_client()
            client.admin.command("ping")
            print("MongoDB connected successfully")
        except Exception as error:
            print("MongoDB connection failed:", error)
            raise

    def close(self) -> None:
        """Closes the client connection."""
        if self._client is not None:
            self._client.close()
            self._client = None
            self._db = None
            print("MongoDB connection closed")


# Default database manager instance
mongo_manager = MongoDBManager()


def connect_to_mongodb() -> None:
    mongo_manager.connect()


def close_mongodb_connection() -> None:
    mongo_manager.close()


def get_todo_collection() -> Collection:
    return mongo_manager.get_collection()


def get_user_collection() -> Collection:
    return mongo_manager.get_collection(settings.USER_COLLECTION_NAME)