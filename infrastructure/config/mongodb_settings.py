"""Loads MongoDB connection details and collection names from environment variables."""
import os

from infrastructure.config.env import load_dotenv  # noqa: F401


class MongoDBSettings:
    """MongoDB-only configuration for the onion architecture adapter."""

    URL = os.getenv("MONGO_URL", "mongodb://127.0.0.1:27017")
    DATABASE_NAME = os.getenv("MONGO_DB_NAME", "todo_db")
    TODO_COLLECTION_NAME = os.getenv("MONGO_COLLECTION_NAME", "todos")
    USER_COLLECTION_NAME = os.getenv("MONGO_USER_COLLECTION_NAME", "users")


mongodb_settings = MongoDBSettings()
