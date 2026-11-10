from typing import List, Optional

from bson import ObjectId
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError, PyMongoError

from application.exceptions import UserAlreadyExistsError, UserRepositoryError
from domain.entities.user import User
from domain.repositories.user_repository import UserRepository
from infrastructure.database.mongodb.client import get_user_collection


class MongoUserRepository(UserRepository):
    def __init__(self, collection: Optional[Collection] = None):
        self._collection = collection if collection is not None else get_user_collection()

    @property
    def collection(self) -> Collection:
        return self._collection

    def ensure_indexes(self) -> None:
        try:
            self.collection.create_index("email", unique=True)
        except PyMongoError as error:
            raise UserRepositoryError("User storage operation failed.") from error

    def create(self, user: User) -> User:
        document = {"email": user.email, "password_hash": user.password_hash}
        if user.id:
            document["_id"] = ObjectId(user.id)
        try:
            result = self.collection.insert_one(document)
        except DuplicateKeyError as error:
            raise UserAlreadyExistsError(
                "An account with this email already exists."
            ) from error
        except PyMongoError as error:
            raise UserRepositoryError("User storage operation failed.") from error

        user.id = str(result.inserted_id)
        return user

    def get_by_email(self, email: str) -> Optional[User]:
        try:
            document = self.collection.find_one({"email": email.strip().lower()})
        except PyMongoError as error:
            raise UserRepositoryError("User storage operation failed.") from error

        if document is None:
            return None
        return User(
            user_id=str(document["_id"]),
            email=document["email"],
            password_hash=document["password_hash"],
        )

    def get_by_id(self, user_id: str) -> Optional[User]:
        if not ObjectId.is_valid(user_id):
            return None
        try:
            document = self.collection.find_one({"_id": ObjectId(user_id)})
        except PyMongoError as error:
            raise UserRepositoryError("User storage operation failed.") from error
        if document is None:
            return None
        return User(
            user_id=str(document["_id"]),
            email=document["email"],
            password_hash=document["password_hash"],
        )

    def new_user_id(self, email: str) -> str:
        return str(ObjectId())

    def list_users(self) -> List[User]:
        try:
            documents = self.collection.find({}, {"email": 1, "password_hash": 1})
            return [
                User(
                    user_id=str(document["_id"]),
                    email=document["email"],
                    password_hash=document.get("password_hash", ""),
                )
                for document in documents
            ]
        except PyMongoError as error:
            raise UserRepositoryError("User storage operation failed.") from error
