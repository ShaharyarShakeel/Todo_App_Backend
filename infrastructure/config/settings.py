import os
import secrets


class Settings:
    """Application and infrastructure configuration loaded from environment variables."""

    MONGO_URL: str = os.getenv("MONGO_URL", "mongodb://127.0.0.1:27017")
    DATABASE_NAME: str = os.getenv("MONGO_DB_NAME", "todo_db")
    TODO_COLLECTION_NAME: str = os.getenv("MONGO_COLLECTION_NAME", "todos")
    USER_COLLECTION_NAME: str = os.getenv("MONGO_USER_COLLECTION_NAME", "users")
    MVC_TODO_COLLECTION_NAME: str = os.getenv("MONGO_MVC_COLLECTION_NAME", "todos_mvc")
    MVC_USER_COLLECTION_NAME: str = os.getenv("MONGO_MVC_USER_COLLECTION_NAME", "users_mvc")
    FIREBASE_CREDENTIALS_PATH: str = os.getenv(
        "GOOGLE_APPLICATION_CREDENTIALS",
        r"D:\Sherry\secretstodoapp-bc42e-firebase-adminsdk-fbsvc-fd557b60c6.json",
    )
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY") or secrets.token_urlsafe(32)
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    )


settings = Settings()
