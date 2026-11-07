import os

from infrastructure.config.env import load_dotenv  # noqa: F401


class FirebaseSettings:
    """Firebase and Firestore-only configuration for the onion adapter."""

    CREDENTIALS_PATH = os.getenv(
        "FIREBASE_CREDENTIALS_PATH",
        r"D:\Sherry\secrets\todoapp-bc42e-firebase-adminsdk-fbsvc-fd557b60c6.json",
    )
    TODO_COLLECTION_NAME = os.getenv("FIREBASE_TODO_COLLECTION", "todos")
    USER_COLLECTION_NAME = os.getenv("FIREBASE_USER_COLLECTION", "users")


firebase_settings = FirebaseSettings()
