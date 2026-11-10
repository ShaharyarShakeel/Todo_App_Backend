"""Manages the Firebase connection by initializing Firebase Admin,
connecting to Firestore, providing the database client, checking
database connectivity, and closing the connection when needed."""
from pathlib import Path
from typing import Optional

import firebase_admin
from firebase_admin import credentials, firestore
from google.api_core.exceptions import GoogleAPIError
from google.cloud.firestore import Client

from infrastructure.config.firebase_settings import firebase_settings


class FirebaseManager:
    """Owns the Firebase Admin app and Firestore client lifecycle."""

    def __init__(self, credentials_path: str = firebase_settings.CREDENTIALS_PATH):
        self.credentials_path = credentials_path
        self._app: Optional[firebase_admin.App] = None
        self._client: Optional[Client] = None

    def connect(self) -> None:
        if self._app is not None:
            return
        if self.credentials_path:
            path = Path(self.credentials_path).expanduser()
            if not path.is_file():
                raise FileNotFoundError(f"Firebase credentials file not found: {path}")
            credential = credentials.Certificate(str(path))
            self._app = firebase_admin.initialize_app(credential)
        else:
            # Supports ADC in deployed environments (for example, Cloud Run).
            self._app = firebase_admin.initialize_app()
        self._client = firestore.client(self._app)
        try:
            # A one-document query confirms Firestore is reachable without loading data.
            self._client.collection(firebase_settings.TODO_COLLECTION_NAME).limit(1).get()
        except GoogleAPIError as error:
            firebase_admin.delete_app(self._app)
            self._app = None
            self._client = None
            print(f"Firebase Firestore connection failed: {error}")
            raise
        print("Firebase Firestore connected successfully")

    def get_client(self) -> Client:
        if self._client is None:
            self.connect()
        return self._client

    def close(self) -> None:
        if self._app is not None:
            firebase_admin.delete_app(self._app)
            self._app = None
            self._client = None


firebase_manager = FirebaseManager()


def connect_to_firebase() -> None:
    firebase_manager.connect()


def close_firebase() -> None:
    firebase_manager.close()


def get_firestore_client() -> Client:
    return firebase_manager.get_client()
