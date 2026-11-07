from typing import List, Optional

from google.api_core.exceptions import GoogleAPIError
from google.cloud.firestore import Client

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

    @staticmethod
    def _to_domain(document) -> Todo:
        data = document.to_dict() or {}
        return Todo(
            todo_id=document.id,
            title=data["title"],
            description=data.get("description"),
            completed=data.get("completed", False),
            owner_id=data.get("owner_id"),
        )
