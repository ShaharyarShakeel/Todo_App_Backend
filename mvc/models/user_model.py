from typing import Optional

from pymongo.errors import DuplicateKeyError, PyMongoError

from mvc.config.database import Database
from mvc.exceptions import UserAlreadyExistsError, UserStorageError


class UserModel:
    def __init__(self, email: str, password_hash: str, user_id: Optional[str] = None):
        self.id = user_id
        self.email = email.strip().lower()
        self.password_hash = password_hash

    @classmethod
    def ensure_indexes(cls) -> None:
        try:
            Database.get_user_collection().create_index("email", unique=True)
        except PyMongoError as error:
            raise UserStorageError("User storage operation failed.") from error

    @classmethod
    def create(cls, email: str, password_hash: str) -> "UserModel":
        normalized_email = email.strip().lower()
        try:
            result = Database.get_user_collection().insert_one(
                {"email": normalized_email, "password_hash": password_hash}
            )
        except DuplicateKeyError as error:
            raise UserAlreadyExistsError(
                "An account with this email already exists."
            ) from error
        except PyMongoError as error:
            raise UserStorageError("User storage operation failed.") from error

        return cls(
            user_id=str(result.inserted_id),
            email=normalized_email,
            password_hash=password_hash,
        )

    @classmethod
    def find_by_email(cls, email: str) -> Optional["UserModel"]:
        try:
            document = Database.get_user_collection().find_one(
                {"email": email.strip().lower()}
            )
        except PyMongoError as error:
            raise UserStorageError("User storage operation failed.") from error

        if document is None:
            return None
        return cls(
            user_id=str(document["_id"]),
            email=document["email"],
            password_hash=document["password_hash"],
        )
