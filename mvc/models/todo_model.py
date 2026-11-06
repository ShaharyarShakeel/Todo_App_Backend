from typing import Optional, List, Dict, Any
from bson import ObjectId
from pymongo.errors import PyMongoError

from mvc.config.database import Database
from mvc.exceptions import InvalidTodoIdError, TodoStorageError

class TodoModel:
    """
    Model in MVC.
    Handles data structure, validation, and direct database queries.
    """

    MAX_TITLE_LENGTH = 200

    def __init__(
        self,
        title: str,
        description: Optional[str] = None,
        completed: bool = False,
        todo_id: Optional[str] = None,
        owner_id: Optional[str] = None,
    ):
        self.id = todo_id
        self.owner_id = owner_id
        self.title = title
        self.description = description
        self.completed = completed

    @classmethod
    def validate_title(cls, title: str) -> str:
        if not title or not title.strip():
            raise ValueError("Title is required and cannot be empty.")
        if len(title.strip()) > cls.MAX_TITLE_LENGTH:
            raise ValueError(f"Title cannot exceed {cls.MAX_TITLE_LENGTH} characters.")
        return title.strip()

    @classmethod
    def create(
        cls, title: str, description: Optional[str], owner_id: str
    ) -> "TodoModel":
        clean_title = cls.validate_title(title)
        clean_desc = description.strip() if description else None

        document = {
            "title": clean_title,
            "description": clean_desc,
            "completed": False,
            "owner_id": owner_id,
        }
        try:
            collection = Database.get_collection()
            result = collection.insert_one(document)
        except PyMongoError as error:
            raise TodoStorageError("Todo storage operation failed.") from error

        return cls(
            todo_id=str(result.inserted_id),
            title=clean_title,
            description=clean_desc,
            completed=False,
            owner_id=owner_id,
        )

    @classmethod
    def find_all(cls, owner_id: str) -> List["TodoModel"]:
        try:
            collection = Database.get_collection()
            documents = collection.find({"owner_id": owner_id})
            return [cls._from_document(doc) for doc in documents]
        except PyMongoError as error:
            raise TodoStorageError("Todo storage operation failed.") from error

    @classmethod
    def find_by_id(cls, todo_id: str, owner_id: str) -> Optional["TodoModel"]:
        if not ObjectId.is_valid(todo_id):
            raise InvalidTodoIdError(f"Todo ID '{todo_id}' is invalid.")

        try:
            collection = Database.get_collection()
            doc = collection.find_one(
                {"_id": ObjectId(todo_id), "owner_id": owner_id}
            )
            if not doc:
                return None
            return cls._from_document(doc)
        except PyMongoError as error:
            raise TodoStorageError("Todo storage operation failed.") from error

    @classmethod
    def update(
        cls,
        todo_id: str,
        title: str,
        description: Optional[str] = None,
        completed: bool = False,
        *,
        owner_id: str,
    ) -> Optional["TodoModel"]:
        if not ObjectId.is_valid(todo_id):
            raise InvalidTodoIdError(f"Todo ID '{todo_id}' is invalid.")

        clean_title = cls.validate_title(title)
        clean_desc = description.strip() if description else None

        try:
            collection = Database.get_collection()
            result = collection.update_one(
                {"_id": ObjectId(todo_id), "owner_id": owner_id},
                {
                    "$set": {
                        "title": clean_title,
                        "description": clean_desc,
                        "completed": completed,
                    }
                },
            )
            if result.matched_count == 0:
                return None
            return cls.find_by_id(todo_id, owner_id)
        except PyMongoError as error:
            raise TodoStorageError("Todo storage operation failed.") from error

    @classmethod
    def patch(
        cls,
        todo_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        completed: Optional[bool] = None,
        *,
        owner_id: str,
    ) -> Optional["TodoModel"]:
        if not ObjectId.is_valid(todo_id):
            raise InvalidTodoIdError(f"Todo ID '{todo_id}' is invalid.")

        update_data: Dict[str, Any] = {}
        if title is not None:
            update_data["title"] = cls.validate_title(title)
        if description is not None:
            update_data["description"] = description.strip() if description else None
        if completed is not None:
            update_data["completed"] = completed

        try:
            if not update_data:
                return cls.find_by_id(todo_id, owner_id)

            collection = Database.get_collection()
            result = collection.update_one(
                {"_id": ObjectId(todo_id), "owner_id": owner_id},
                {"$set": update_data},
            )
            if result.matched_count == 0:
                return None
            return cls.find_by_id(todo_id, owner_id)
        except PyMongoError as error:
            raise TodoStorageError("Todo storage operation failed.") from error

    @classmethod
    def delete(cls, todo_id: str, owner_id: str) -> bool:
        if not ObjectId.is_valid(todo_id):
            raise InvalidTodoIdError(f"Todo ID '{todo_id}' is invalid.")

        try:
            collection = Database.get_collection()
            result = collection.delete_one(
                {"_id": ObjectId(todo_id), "owner_id": owner_id}
            )
            return result.deleted_count > 0
        except PyMongoError as error:
            raise TodoStorageError("Todo storage operation failed.") from error

    @classmethod
    def _from_document(cls, doc: dict) -> "TodoModel":
        return cls(
            todo_id=str(doc["_id"]),
            title=doc["title"],
            description=doc.get("description"),
            completed=doc.get("completed", False),
            owner_id=doc.get("owner_id"),
        )
