import os
from pymongo import MongoClient

class Database:
    """Manages the MongoDB connection for the MVC architecture."""
    
    MONGO_URL = os.getenv("MONGO_URL", "mongodb://127.0.0.1:27017")
    DB_NAME = os.getenv("MONGO_DB_NAME", "todo_db")
    COLLECTION_NAME = "todos_mvc"
    USER_COLLECTION_NAME = os.getenv("MONGO_MVC_USER_COLLECTION_NAME", "users_mvc")

    _client = None

    @classmethod
    def get_client(cls):
        if cls._client is None:
            cls._client = MongoClient(cls.MONGO_URL)
        return cls._client

    @classmethod
    def get_collection(cls):
        client = cls.get_client()
        return client[cls.DB_NAME][cls.COLLECTION_NAME]

    @classmethod
    def get_user_collection(cls):
        client = cls.get_client()
        return client[cls.DB_NAME][cls.USER_COLLECTION_NAME]

    @classmethod
    def close(cls):
        if cls._client is not None:
            cls._client.close()
            cls._client = None
