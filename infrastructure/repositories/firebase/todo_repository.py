from datetime import date, datetime, timezone
from typing import List, Optional

from google.api_core.exceptions import GoogleAPIError
from google.cloud.firestore import Client, transactional

from application.exceptions import TodoRepositoryError
from domain.entities.todo import Todo
from domain.exceptions.todo_exceptions import InvalidTodoIdError
from domain.repositories.todo_repository import TodoRepository
from infrastructure.config.firebase_settings import firebase_settings
from infrastructure.database.firebase.client import get_firestore_client


class FirebaseTodoRepository(TodoRepository):
    """Firestore adapter for the onion architecture's TodoRepository port."""

    def __init__(self, client: Optional[Client] = None):
        self._client = client
        self._collection = None

    @property
    def collection(self):
        if self._collection is None:
            client = self._client or get_firestore_client()
            self._client = client
            self._collection = client.collection(firebase_settings.TODO_COLLECTION_NAME)
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
            reference = self.collection.document()
            reference.set(document)
        except GoogleAPIError as error:
            raise TodoRepositoryError("Todo storage operation failed.") from error
        todo.id = reference.id
        return todo

    def get_all(self, owner_id: str) -> List[Todo]:
        try:
            documents = self.collection.where("owner_id", "==", owner_id).stream()
            return [self._to_domain(document) for document in documents]
        except GoogleAPIError as error:
            raise TodoRepositoryError("Todo storage operation failed.") from error

    def get_by_id(self, todo_id: str, owner_id: str) -> Optional[Todo]:
        if not todo_id or "/" in todo_id:
            raise InvalidTodoIdError(f"Todo ID '{todo_id}' is invalid.")
        try:
            snapshot = self.collection.document(todo_id).get()
            if not snapshot.exists:
                return None
            data = snapshot.to_dict() or {}
            if data.get("owner_id") != owner_id:
                return None
            return self._to_domain(snapshot)
        except GoogleAPIError as error:
            raise TodoRepositoryError("Todo storage operation failed.") from error

    def update(self, todo: Todo) -> Optional[Todo]:
        if not todo.id or "/" in todo.id:
            raise InvalidTodoIdError(f"Todo ID '{todo.id}' is invalid.")
        try:
            reference = self.collection.document(todo.id)
            snapshot = reference.get()
            if not snapshot.exists or (snapshot.to_dict() or {}).get("owner_id") != todo.owner_id:
                return None
            reference.update({
                "title": todo.title,
                "description": todo.description,
                "completed": todo.completed,
                "due_date": todo.due_date.isoformat() if todo.due_date else None,
                "reminder_due_at": todo.reminder_due_at,
                "reminder_sent_at": todo.reminder_sent_at,
                "reminder_claimed_until": todo.reminder_claimed_until,
                "reminder_claim_id": todo.reminder_claim_id,
            })
            return self.get_by_id(todo.id, todo.owner_id)
        except GoogleAPIError as error:
            raise TodoRepositoryError("Todo storage operation failed.") from error

    def delete(self, todo_id: str, owner_id: str) -> bool:
        if not todo_id or "/" in todo_id:
            raise InvalidTodoIdError(f"Todo ID '{todo_id}' is invalid.")
        try:
            reference = self.collection.document(todo_id)
            snapshot = reference.get()
            if not snapshot.exists or (snapshot.to_dict() or {}).get("owner_id") != owner_id:
                return False
            reference.delete()
            return True
        except GoogleAPIError as error:
            raise TodoRepositoryError("Todo storage operation failed.") from error

    def get_unscheduled_reminders(self, limit: int) -> List[Todo]:
        try:
            todos = []
            for document in self.collection.where("completed", "==", False).stream():
                data = document.to_dict() or {}
                if (
                    data.get("due_date")
                    and not data.get("reminder_due_at")
                    and len(todos) < limit
                ):
                    todos.append(self._to_domain(document))
                if len(todos) >= limit:
                    break
            return todos
        except GoogleAPIError as error:
            raise TodoRepositoryError("Todo storage operation failed.") from error

    def schedule_reminder(
        self, todo_id: str, due_date: date, reminder_due_at: datetime
    ) -> bool:
        reference = self._document_reference(todo_id)
        transaction = self._client_or_create().transaction()

        @transactional
        def schedule(transaction):
            snapshot = reference.get(transaction=transaction)
            if not snapshot.exists:
                return False
            data = snapshot.to_dict() or {}
            if (
                data.get("completed", False)
                or data.get("due_date") != due_date.isoformat()
                or data.get("reminder_due_at") is not None
            ):
                return False
            transaction.update(
                reference,
                {
                    "reminder_due_at": reminder_due_at,
                    "reminder_sent_at": None,
                    "reminder_claimed_until": None,
                    "reminder_claim_id": None,
                },
            )
            return True

        try:
            return schedule(transaction)
        except GoogleAPIError as error:
            raise TodoRepositoryError("Todo storage operation failed.") from error

    def claim_due_reminders(
        self, now: datetime, lease_until: datetime, claim_id: str, limit: int
    ) -> List[Todo]:
        claimed = []
        try:
            candidates = []
            for document in self.collection.where("completed", "==", False).stream():
                data = document.to_dict() or {}
                due_at = self._as_utc(data.get("reminder_due_at"))
                claim_until = self._as_utc(data.get("reminder_claimed_until"))
                if (
                    due_at is not None
                    and due_at <= now
                    and data.get("reminder_sent_at") is None
                    and (claim_until is None or claim_until <= now)
                ):
                    candidates.append((due_at, document))
            candidates.sort(key=lambda candidate: candidate[0])

            for _, document in candidates:
                if len(claimed) >= limit:
                    break
                reference = document.reference
                transaction = self._client_or_create().transaction()

                @transactional
                def claim(transaction):
                    snapshot = reference.get(transaction=transaction)
                    if not snapshot.exists:
                        return None
                    data = snapshot.to_dict() or {}
                    due_at = self._as_utc(data.get("reminder_due_at"))
                    current_claim = self._as_utc(data.get("reminder_claimed_until"))
                    if (
                        data.get("completed", False)
                        or due_at is None
                        or due_at > now
                        or data.get("reminder_sent_at") is not None
                        or (current_claim is not None and current_claim > now)
                    ):
                        return None
                    transaction.update(
                        reference,
                        {
                            "reminder_claimed_until": lease_until,
                            "reminder_claim_id": claim_id,
                        },
                    )
                    data["reminder_claimed_until"] = lease_until
                    data["reminder_claim_id"] = claim_id
                    return self._to_domain_data(snapshot.id, data)

                todo = claim(transaction)
                if todo is not None:
                    claimed.append(todo)
            return claimed
        except GoogleAPIError as error:
            raise TodoRepositoryError("Todo storage operation failed.") from error

    def mark_reminder_sent(
        self,
        todo_id: str,
        reminder_due_at: datetime,
        claim_id: str,
        sent_at: datetime,
    ) -> bool:
        reference = self._document_reference(todo_id)
        transaction = self._client_or_create().transaction()

        @transactional
        def mark(transaction):
            snapshot = reference.get(transaction=transaction)
            if not snapshot.exists:
                return False
            data = snapshot.to_dict() or {}
            if (
                data.get("completed", False)
                or data.get("reminder_sent_at") is not None
                or data.get("reminder_claim_id") != claim_id
                or self._as_utc(data.get("reminder_due_at")) != reminder_due_at
            ):
                return False
            transaction.update(
                reference,
                {
                    "reminder_sent_at": sent_at,
                    "reminder_claimed_until": None,
                    "reminder_claim_id": None,
                },
            )
            return True

        try:
            return mark(transaction)
        except GoogleAPIError as error:
            raise TodoRepositoryError("Todo storage operation failed.") from error

    def release_reminder_claim(
        self, todo_id: str, reminder_due_at: datetime, claim_id: str
    ) -> bool:
        reference = self._document_reference(todo_id)
        transaction = self._client_or_create().transaction()

        @transactional
        def release(transaction):
            snapshot = reference.get(transaction=transaction)
            if not snapshot.exists:
                return False
            data = snapshot.to_dict() or {}
            if (
                data.get("reminder_sent_at") is not None
                or data.get("reminder_claim_id") != claim_id
                or self._as_utc(data.get("reminder_due_at")) != reminder_due_at
            ):
                return False
            transaction.update(
                reference,
                {"reminder_claimed_until": None, "reminder_claim_id": None},
            )
            return True

        try:
            return release(transaction)
        except GoogleAPIError as error:
            raise TodoRepositoryError("Todo storage operation failed.") from error

    def _client_or_create(self):
        if self._client is None:
            self._client = get_firestore_client()
        return self._client

    def _document_reference(self, todo_id: str):
        if not todo_id or "/" in todo_id:
            raise InvalidTodoIdError(f"Todo ID '{todo_id}' is invalid.")
        return self.collection.document(todo_id)

    @staticmethod
    def _as_utc(value):
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @staticmethod
    def _to_domain(document) -> Todo:
        data = document.to_dict() or {}
        return FirebaseTodoRepository._to_domain_data(document.id, data)

    @staticmethod
    def _to_domain_data(document_id: str, data: dict) -> Todo:
        return Todo(
            todo_id=document_id,
            title=data["title"],
            description=data.get("description"),
            completed=data.get("completed", False),
            owner_id=data.get("owner_id"),
            due_date=(
                date.fromisoformat(data["due_date"])
                if data.get("due_date")
                else None
            ),
            reminder_due_at=FirebaseTodoRepository._as_utc(
                data.get("reminder_due_at")
            ),
            reminder_sent_at=FirebaseTodoRepository._as_utc(
                data.get("reminder_sent_at")
            ),
            reminder_claimed_until=FirebaseTodoRepository._as_utc(
                data.get("reminder_claimed_until")
            ),
            reminder_claim_id=data.get("reminder_claim_id"),
        )
