from typing import List, Optional
from bson import ObjectId
from pymongo.collection import Collection
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

    @staticmethod
    def _to_domain(document: dict) -> Todo:
        return Todo(
            todo_id=str(document["_id"]),
            title=document["title"],
            description=document.get("description"),
            completed=document.get("completed", False),
            owner_id=document.get("owner_id"),
        )
