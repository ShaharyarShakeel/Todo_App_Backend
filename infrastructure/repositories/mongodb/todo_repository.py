from datetime import date, datetime, timezone
from typing import List, Optional
from bson import ObjectId
from pymongo.collection import Collection
from pymongo import ReturnDocument
from pymongo.errors import PyMongoError

from application.exceptions import TodoRepositoryError
from domain.entities.todo import Todo
from domain.exceptions.todo_exceptions import InvalidTodoIdError
from domain.repositories.todo_repository import TodoRepository
from infrastructure.database.mongodb.client import get_todo_collection


class MongoTodoRepository(TodoRepository):
    """
    MongoDB implementation of the TodoRepository interface (Adapter).
    
    Adheres to the Dependency Inversion Principle by implementing
    the domain TodoRepository interface.
    Accepts collection via Dependency Injection.
    """

    def __init__(self, collection: Optional[Collection] = None):
        self._collection = collection if collection is not None else get_todo_collection()

    @property
    def collection(self) -> Collection:
        return self._collection

    def create(self, todo: Todo) -> Todo:
        document = {
            "title": todo.title,
            "description": todo.description,
            "completed": todo.completed,
            "due_date": todo.due_date.isoformat() if todo.due_date else None,
            "reminder_due_at": todo.reminder_due_at,
            "reminder_sent_at": todo.reminder_sent_at,
            "reminder_claimed_until": todo.reminder_claimed_until,
            "reminder_claim_id": todo.reminder_claim_id,
            "owner_id": todo.owner_id,
        }
        try:
            result = self.collection.insert_one(document)
        except PyMongoError as error:
            raise TodoRepositoryError("Todo storage operation failed.") from error

        todo.id = str(result.inserted_id)
        return todo

    def get_all(self, owner_id: str) -> List[Todo]:
        try:
            documents = self.collection.find({"owner_id": owner_id})
            return [self._to_domain(doc) for doc in documents]
        except PyMongoError as error:
            raise TodoRepositoryError("Todo storage operation failed.") from error

    def get_by_id(self, todo_id: str, owner_id: str) -> Optional[Todo]:
        if not ObjectId.is_valid(todo_id):
            raise InvalidTodoIdError(f"Todo ID '{todo_id}' is invalid.")

        try:
            document = self.collection.find_one(
                {"_id": ObjectId(todo_id), "owner_id": owner_id}
            )
            if not document:
                return None

            return self._to_domain(document)
        except PyMongoError as error:
            raise TodoRepositoryError("Todo storage operation failed.") from error

    def update(self, todo: Todo) -> Optional[Todo]:
        if not todo.id or not ObjectId.is_valid(todo.id):
            raise InvalidTodoIdError(f"Todo ID '{todo.id}' is invalid.")

        try:
            result = self.collection.update_one(
                {"_id": ObjectId(todo.id), "owner_id": todo.owner_id},
                {
                    "$set": {
                        "title": todo.title,
                        "description": todo.description,
                        "completed": todo.completed,
                        "due_date": todo.due_date.isoformat() if todo.due_date else None,
                        "reminder_due_at": todo.reminder_due_at,
                        "reminder_sent_at": todo.reminder_sent_at,
                        "reminder_claimed_until": todo.reminder_claimed_until,
                        "reminder_claim_id": todo.reminder_claim_id,
                    }
                },
            )

            if result.matched_count == 0:
                return None

            return self.get_by_id(todo.id, todo.owner_id)
        except PyMongoError as error:
            raise TodoRepositoryError("Todo storage operation failed.") from error

    def delete(self, todo_id: str, owner_id: str) -> bool:
        if not ObjectId.is_valid(todo_id):
            raise InvalidTodoIdError(f"Todo ID '{todo_id}' is invalid.")

        try:
            result = self.collection.delete_one(
                {"_id": ObjectId(todo_id), "owner_id": owner_id}
            )
            return result.deleted_count > 0
        except PyMongoError as error:
            raise TodoRepositoryError("Todo storage operation failed.") from error

    def get_unscheduled_reminders(self, limit: int) -> List[Todo]:
        try:
            documents = self.collection.find(
                {
                    "completed": {"$ne": True},
                    "due_date": {"$ne": None},
                    "$or": [
                        {"reminder_due_at": {"$exists": False}},
                        {"reminder_due_at": None},
                    ],
                }
            ).limit(limit)
            return [self._to_domain(document) for document in documents]
        except PyMongoError as error:
            raise TodoRepositoryError("Todo storage operation failed.") from error

    def schedule_reminder(
        self, todo_id: str, due_date: date, reminder_due_at: datetime
    ) -> bool:
        if not ObjectId.is_valid(todo_id):
            raise InvalidTodoIdError(f"Todo ID '{todo_id}' is invalid.")
        try:
            result = self.collection.update_one(
                {
                    "_id": ObjectId(todo_id),
                    "due_date": due_date.isoformat(),
                    "completed": {"$ne": True},
                    "$or": [
                        {"reminder_due_at": {"$exists": False}},
                        {"reminder_due_at": None},
                    ],
                },
                {
                    "$set": {
                        "reminder_due_at": reminder_due_at,
                        "reminder_sent_at": None,
                        "reminder_claimed_until": None,
                        "reminder_claim_id": None,
                    }
                },
            )
            return result.modified_count > 0
        except PyMongoError as error:
            raise TodoRepositoryError("Todo storage operation failed.") from error

    def claim_due_reminders(
        self, now: datetime, lease_until: datetime, claim_id: str, limit: int
    ) -> List[Todo]:
        eligible = {
            "completed": {"$ne": True},
            "reminder_due_at": {"$lte": now},
            "$and": [
                {
                    "$or": [
                        {"reminder_sent_at": {"$exists": False}},
                        {"reminder_sent_at": None},
                    ]
                },
                {
                    "$or": [
                        {"reminder_claimed_until": {"$exists": False}},
                        {"reminder_claimed_until": None},
                        {"reminder_claimed_until": {"$lte": now}},
                    ]
                },
            ],
        }
        claimed = []
        try:
            candidates = self.collection.find(eligible).sort("reminder_due_at", 1).limit(limit)
            for candidate in candidates:
                query = dict(eligible, _id=candidate["_id"])
                document = self.collection.find_one_and_update(
                    query,
                    {
                        "$set": {
                            "reminder_claimed_until": lease_until,
                            "reminder_claim_id": claim_id,
                        }
                    },
                    return_document=ReturnDocument.AFTER,
                )
                if document:
                    claimed.append(self._to_domain(document))
            return claimed
        except PyMongoError as error:
            raise TodoRepositoryError("Todo storage operation failed.") from error

    def mark_reminder_sent(
        self,
        todo_id: str,
        reminder_due_at: datetime,
        claim_id: str,
        sent_at: datetime,
    ) -> bool:
        if not ObjectId.is_valid(todo_id):
            raise InvalidTodoIdError(f"Todo ID '{todo_id}' is invalid.")
        try:
            result = self.collection.update_one(
                {
                    "_id": ObjectId(todo_id),
                    "reminder_due_at": reminder_due_at,
                    "reminder_claim_id": claim_id,
                    "reminder_sent_at": None,
                    "completed": {"$ne": True},
                },
                {
                    "$set": {"reminder_sent_at": sent_at},
                    "$unset": {
                        "reminder_claimed_until": "",
                        "reminder_claim_id": "",
                    },
                },
            )
            return result.modified_count > 0
        except PyMongoError as error:
            raise TodoRepositoryError("Todo storage operation failed.") from error

    def release_reminder_claim(
        self, todo_id: str, reminder_due_at: datetime, claim_id: str
    ) -> bool:
        if not ObjectId.is_valid(todo_id):
            raise InvalidTodoIdError(f"Todo ID '{todo_id}' is invalid.")
        try:
            result = self.collection.update_one(
                {
                    "_id": ObjectId(todo_id),
                    "reminder_due_at": reminder_due_at,
                    "reminder_claim_id": claim_id,
                    "reminder_sent_at": None,
                },
                {
                    "$unset": {
                        "reminder_claimed_until": "",
                        "reminder_claim_id": "",
                    }
                },
            )
            return result.modified_count > 0
        except PyMongoError as error:
            raise TodoRepositoryError("Todo storage operation failed.") from error

    @staticmethod
    def _to_domain(document: dict) -> Todo:
        def as_utc(value):
            if value is None:
                return None
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)

        return Todo(
            todo_id=str(document["_id"]),
            title=document["title"],
            description=document.get("description"),
            completed=document.get("completed", False),
            owner_id=document.get("owner_id"),
            due_date=(
                date.fromisoformat(document["due_date"])
                if document.get("due_date")
                else None
            ),
            reminder_due_at=as_utc(document.get("reminder_due_at")),
            reminder_sent_at=as_utc(document.get("reminder_sent_at")),
            reminder_claimed_until=as_utc(document.get("reminder_claimed_until")),
            reminder_claim_id=document.get("reminder_claim_id"),
        )
