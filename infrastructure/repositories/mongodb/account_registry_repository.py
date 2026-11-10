from typing import List, Optional

from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError, PyMongoError

from application.exceptions import (
    AccountRegistryConflictError,
    UserAlreadyExistsError,
    UserRepositoryError,
)
from domain.entities.account_assignment import AccountAssignment
from domain.repositories.account_registry import AccountRegistry
from infrastructure.database.mongodb.client import get_account_registry_collection


class MongoAccountRegistryRepository(AccountRegistry):
    """MongoDB metadata-only registry for global accounts and their provider."""

    def __init__(self, collection: Optional[Collection] = None):
        self.collection = collection if collection is not None else get_account_registry_collection()

    def ensure_indexes(self) -> None:
        try:
            # Migrate the former global email uniqueness index to provider-scoped
            # uniqueness. This changes index metadata only; no registry documents
            # or user/Todo records are removed.
            for index in self.collection.list_indexes():
                keys = list(index.get("key", {}).items())
                if keys == [("email_normalized", 1)] and index.get("unique"):
                    self.collection.drop_index(index["name"])
            self.collection.create_index("user_id", unique=True)
            self.collection.create_index(
                [("email_normalized", 1), ("provider", 1)], unique=True
            )
        except PyMongoError as error:
            if getattr(error, "code", None) in (11000, 11001) or isinstance(error, DuplicateKeyError):
                raise AccountRegistryConflictError(
                    "The existing account_registry contains duplicate global user IDs or "
                    "duplicate normalized emails within a provider. Resolve those records "
                    "before starting the API."
                ) from error
            raise UserRepositoryError("Account registry operation failed.") from error

    def reserve(self, assignment: AccountAssignment) -> None:
        document = self._to_document(assignment)
        document["status"] = "pending"
        try:
            self.collection.insert_one(document)
        except DuplicateKeyError as error:
            raise UserAlreadyExistsError(
                "An account with this email or user ID already exists."
            ) from error
        except PyMongoError as error:
            raise UserRepositoryError("Account registry operation failed.") from error

    def activate(self, user_id: str) -> None:
        try:
            result = self.collection.update_one(
                {"user_id": user_id, "status": "pending"},
                {"$set": {"status": "active"}},
            )
            if result.matched_count == 0:
                existing = self.collection.find_one({"user_id": user_id, "status": "active"})
                if existing is None:
                    raise UserRepositoryError("Pending account reservation was not found.")
        except PyMongoError as error:
            raise UserRepositoryError("Account registry operation failed.") from error

    def delete_pending(self, user_id: str) -> None:
        try:
            self.collection.delete_one({"user_id": user_id, "status": "pending"})
        except PyMongoError as error:
            raise UserRepositoryError("Account registry operation failed.") from error

    def add_existing(self, assignment: AccountAssignment) -> None:
        document = self._to_document(assignment)
        document["status"] = "active"
        try:
            self.collection.insert_one(document)
        except DuplicateKeyError as error:
            raise UserAlreadyExistsError(
                "An account with this email or user ID already exists in the registry."
            ) from error
        except PyMongoError as error:
            raise UserRepositoryError("Account registry operation failed.") from error

    def get_by_email(
        self, email_normalized: str, provider: str
    ) -> Optional[AccountAssignment]:
        return self._find_one(
            {"email_normalized": email_normalized, "provider": provider}
        )

    def get_by_user_id(self, user_id: str) -> Optional[AccountAssignment]:
        return self._find_one({"user_id": user_id})

    def get_by_provider_user_id(self, provider_user_id: str) -> List[AccountAssignment]:
        try:
            return [
                self._from_document(document)
                for document in self.collection.find(
                    {"provider_user_id": provider_user_id, "status": "active"}
                )
            ]
        except PyMongoError as error:
            raise UserRepositoryError("Account registry operation failed.") from error

    def list_all(self) -> List[AccountAssignment]:
        try:
            return [
                self._from_document(document)
                for document in self.collection.find({"status": "active"})
            ]
        except PyMongoError as error:
            raise UserRepositoryError("Account registry operation failed.") from error

    def list_pending(self) -> List[AccountAssignment]:
        try:
            return [
                self._from_document(document)
                for document in self.collection.find({"status": "pending"})
            ]
        except PyMongoError as error:
            raise UserRepositoryError("Account registry operation failed.") from error

    def _find_one(self, query: dict) -> Optional[AccountAssignment]:
        try:
            document = self.collection.find_one(query)
        except PyMongoError as error:
            raise UserRepositoryError("Account registry operation failed.") from error
        return self._from_document(document) if document else None

    @staticmethod
    def _to_document(assignment: AccountAssignment) -> dict:
        return {
            "user_id": assignment.user_id,
            "email_normalized": assignment.email_normalized,
            "provider": assignment.provider,
            "provider_user_id": assignment.provider_user_id,
        }

    @staticmethod
    def _from_document(document: dict) -> AccountAssignment:
        return AccountAssignment(
            user_id=document["user_id"],
            email_normalized=document["email_normalized"],
            provider=document["provider"],
            provider_user_id=document["provider_user_id"],
            status=document.get("status", "active"),
        )
