from pymongo import MongoClient
from infrastructure.config.settings import settings

class Database:
    """Manages the MongoDB connection for the MVC architecture."""
    
    MONGO_URL = settings.MONGO_URL
    DB_NAME = settings.DATABASE_NAME
    COLLECTION_NAME = settings.MVC_TODO_COLLECTION_NAME
    USER_COLLECTION_NAME = settings.MVC_USER_COLLECTION_NAME

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
