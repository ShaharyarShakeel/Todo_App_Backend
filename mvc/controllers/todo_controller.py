from typing import List, Dict, Any
from fastapi import HTTPException, status
from mvc.exceptions import InvalidTodoIdError, TodoStorageError
from mvc.models.todo_model import TodoModel
from mvc.views.todo_view import (
    TodoCreateView,
    TodoUpdateView,
    TodoPatchView,
    TodoView,
)

class TodoController:
    @staticmethod
    def _storage_unavailable() -> HTTPException:
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Todo storage is temporarily unavailable.",
        )

    @staticmethod
    def create_todo(payload: TodoCreateView, owner_id: str) -> Dict[str, Any]:
        try:
            todo = TodoModel.create(
                title=payload.title,
                description=payload.description,
                owner_id=owner_id,
            )
            return TodoView.render_todo(todo)
        except TodoStorageError:
            raise TodoController._storage_unavailable()
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(err),
            )

    @staticmethod
    def get_all_todos(owner_id: str) -> List[Dict[str, Any]]:
        try:
            todos = TodoModel.find_all(owner_id)
            return TodoView.render_todos(todos)
        except TodoStorageError:
            raise TodoController._storage_unavailable()

    @staticmethod
    def get_todo_by_id(todo_id: str, owner_id: str) -> Dict[str, Any]:
        try:
            todo = TodoModel.find_by_id(todo_id, owner_id)
        except InvalidTodoIdError as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(err),
            )
        except TodoStorageError:
            raise TodoController._storage_unavailable()
        if not todo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Todo with id '{todo_id}' not found.",
            )
        return TodoView.render_todo(todo)

    @staticmethod
    def update_todo(
        todo_id: str, payload: TodoUpdateView, owner_id: str
    ) -> Dict[str, Any]:
        try:
            todo = TodoModel.update(
                todo_id=todo_id,
                title=payload.title,
                description=payload.description,
                completed=payload.completed,
                owner_id=owner_id,
            )
            if not todo:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Todo with id '{todo_id}' not found.",
                )
            return TodoView.render_todo(todo)
        except TodoStorageError:
            raise TodoController._storage_unavailable()
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(err),
            )

    @staticmethod
    def patch_todo(
        todo_id: str, payload: TodoPatchView, owner_id: str
    ) -> Dict[str, Any]:
        try:
            todo = TodoModel.patch(
                todo_id=todo_id,
                title=payload.title,
                description=payload.description,
                completed=payload.completed,
                owner_id=owner_id,
            )
            if not todo:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Todo with id '{todo_id}' not found.",
                )
            return TodoView.render_todo(todo)
        except TodoStorageError:
            raise TodoController._storage_unavailable()
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(err),
            )

    @staticmethod
    def delete_todo(todo_id: str, owner_id: str) -> Dict[str, str]:
        try:
            deleted = TodoModel.delete(todo_id, owner_id)
        except TodoStorageError:
            raise TodoController._storage_unavailable()
        except InvalidTodoIdError as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(err),
            )

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Todo with id '{todo_id}' not found.",
            )
        return TodoView.render_message("Todo deleted successfully")
