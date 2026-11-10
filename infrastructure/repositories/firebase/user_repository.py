import hashlib
from typing import List, Optional

from google.api_core.exceptions import GoogleAPIError
from google.cloud.firestore import Client, transactional

from application.exceptions import UserAlreadyExistsError, UserRepositoryError
from domain.entities.user import User
from domain.repositories.user_repository import UserRepository
from infrastructure.config.firebase_settings import firebase_settings
from infrastructure.database.firebase.client import get_firestore_client


class FirebaseUserRepository(UserRepository):
    """Firestore adapter; a stable email document key enforces uniqueness."""

    def __init__(self, client: Optional[Client] = None):
        self._client = client
        self._collection = None

    @property
    def collection(self):
        if self._collection is None:
            self._client = self._client or get_firestore_client()
            self._collection = self._client.collection(firebase_settings.USER_COLLECTION_NAME)
        return self._collection

    @staticmethod
    def _document_id(email: str) -> str:
        return hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()

    def ensure_indexes(self) -> None:
        # Firestore document keys provide the uniqueness needed for email lookup.
        return None

    def create(self, user: User) -> User:
        email = user.email.strip().lower()
        document_id = user.id or self._document_id(email)
        reference = self.collection.document(document_id)
        try:
            client = self._client or get_firestore_client()
            self._client = client
            transaction = client.transaction()

            @transactional
            def create_if_missing(transaction):
                if reference.get(transaction=transaction).exists:
                    raise UserAlreadyExistsError("An account with this email already exists.")
                transaction.create(reference, {"email": email, "password_hash": user.password_hash})

            create_if_missing(transaction)
        except UserAlreadyExistsError:
            raise
        except GoogleAPIError as error:
            raise UserRepositoryError("User storage operation failed.") from error
        user.id = document_id
        return user

    def get_by_email(self, email: str) -> Optional[User]:
        normalized_email = email.strip().lower()
        try:
            snapshot = self.collection.document(self._document_id(normalized_email)).get()
        except GoogleAPIError as error:
            raise UserRepositoryError("User storage operation failed.") from error
        if not snapshot.exists:
            return None
        data = snapshot.to_dict() or {}
        return User(
            user_id=snapshot.id,
            email=data["email"],
            password_hash=data["password_hash"],
        )

    def get_by_id(self, user_id: str) -> Optional[User]:
        if not user_id or "/" in user_id:
            return None
        try:
            snapshot = self.collection.document(user_id).get()
        except GoogleAPIError as error:
            raise UserRepositoryError("User storage operation failed.") from error
        if not snapshot.exists:
            return None
        data = snapshot.to_dict() or {}
        return User(
            user_id=snapshot.id,
            email=data["email"],
            password_hash=data["password_hash"],
        )

    def new_user_id(self, email: str) -> str:
        return self._document_id(email)

    def list_users(self) -> List[User]:
        try:
            return [
                User(
                    user_id=document.id,
                    email=(document.to_dict() or {})["email"],
                    password_hash=(document.to_dict() or {}).get("password_hash", ""),
                )
                for document in self.collection.stream()
            ]
        except GoogleAPIError as error:
            raise UserRepositoryError("User storage operation failed.") from error
