from typing import List, Dict
from fastapi import HTTPException, status

from application.use_cases.create_todo import CreateTodo
from application.use_cases.get_todo import GetTodo
from application.use_cases.get_all_todos import GetAllTodos
from application.use_cases.update_todo import UpdateTodo
from application.use_cases.patch_todo import PatchTodo
from application.use_cases.delete_todo import DeleteTodo
from application.exceptions import TodoRepositoryError
from domain.exceptions.todo_exceptions import (
    DomainException,
    TodoNotFoundError,
)
from application.dtos.todo_dto import (
    TodoCreateDTO,
    TodoUpdateDTO,
    TodoPatchDTO,
    TodoDTO,
)
from presentation.schemas.todo_schema import (
    TodoCreateSchema,
    TodoUpdateSchema,
    TodoPatchSchema,
)


class TodoController:
    """
    Presentation controller for Todo operations.
    
    Translates HTTP inputs/DTOs to application use case calls,
    and maps domain exceptions to appropriate HTTP responses.
    """

    def __init__(
        self,
        create_todo: CreateTodo,
        get_todo: GetTodo,
        get_all_todos: GetAllTodos,
        update_todo: UpdateTodo,
        patch_todo: PatchTodo,
        delete_todo: DeleteTodo,
    ):
        self.create_todo = create_todo
        self.get_todo = get_todo
        self.get_all_todos = get_all_todos
        self.update_todo = update_todo
        self.patch_todo = patch_todo
        self.delete_todo = delete_todo

    def create(self, data: TodoCreateSchema, owner_id: str) -> TodoDTO:
        print("[2. CONTROLLER]       TodoController.create() called")
        print("[2. CONTROLLER]       Converting TodoCreateSchema -> TodoCreateDTO")
        try:
            request = TodoCreateDTO(
                title=data.title,
                description=data.description,
            )
            print("[2. CONTROLLER]       Calling Use Case: CreateTodo.execute(...)")
            result = self.create_todo.execute(request, owner_id)
            print(f"[2. CONTROLLER]       Received TodoDTO(id='{result.id}') from Use Case, passing to Route")
            return result
        except TodoRepositoryError:
            print("[2. CONTROLLER]       Caught TodoRepositoryError -> Raising HTTP 503")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Todo storage is temporarily unavailable.",
            )
        except DomainException as error:
            print(f"[2. CONTROLLER]       Caught DomainException ({error}) -> Raising HTTP 400")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(error),
            )

    def get_all(self, owner_id: str) -> List[TodoDTO]:
        print(f"[2. CONTROLLER]       TodoController.get_all() called for Owner ID: '{owner_id}'")
        print("[2. CONTROLLER]       Calling Use Case: GetAllTodos.execute(...)")
        try:
            result = self.get_all_todos.execute(owner_id)
            print(f"[2. CONTROLLER]       Received {len(result)} TodoDTO(s) from Use Case, passing to Route")
            return result
        except TodoRepositoryError:
            print("[2. CONTROLLER]       Caught TodoRepositoryError -> Raising HTTP 503")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Todo storage is temporarily unavailable.",
            )

    def get_by_id(self, todo_id: str, owner_id: str) -> TodoDTO:
        print(f"[2. CONTROLLER]       TodoController.get_by_id() called for todo_id='{todo_id}'")
        print("[2. CONTROLLER]       Calling Use Case: GetTodo.execute(...)")
        try:
            result = self.get_todo.execute(todo_id=todo_id, owner_id=owner_id)
            print(f"[2. CONTROLLER]       Received TodoDTO(id='{result.id}') from Use Case, passing to Route")
            return result
        except TodoRepositoryError:
            print("[2. CONTROLLER]       Caught TodoRepositoryError -> Raising HTTP 503")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Todo storage is temporarily unavailable.",
            )
        except TodoNotFoundError as error:
            print(f"[2. CONTROLLER]       Caught TodoNotFoundError -> Raising HTTP 404")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(error),
            )
        except DomainException as error:
            print(f"[2. CONTROLLER]       Caught DomainException ({error}) -> Raising HTTP 400")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(error),
            )

    def update(
        self, todo_id: str, data: TodoUpdateSchema, owner_id: str
    ) -> TodoDTO:
        print(f"[2. CONTROLLER]       TodoController.update() called for todo_id='{todo_id}'")
        print("[2. CONTROLLER]       Converting TodoUpdateSchema -> TodoUpdateDTO")
        try:
            request = TodoUpdateDTO(
                todo_id=todo_id,
                title=data.title,
                description=data.description,
                completed=data.completed,
            )
            print("[2. CONTROLLER]       Calling Use Case: UpdateTodo.execute(...)")
            result = self.update_todo.execute(request, owner_id)
            print(f"[2. CONTROLLER]       Received updated TodoDTO(id='{result.id}') from Use Case, passing to Route")
            return result
        except TodoRepositoryError:
            print("[2. CONTROLLER]       Caught TodoRepositoryError -> Raising HTTP 503")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Todo storage is temporarily unavailable.",
            )
        except TodoNotFoundError as error:
            print(f"[2. CONTROLLER]       Caught TodoNotFoundError -> Raising HTTP 404")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(error),
            )
        except DomainException as error:
            print(f"[2. CONTROLLER]       Caught DomainException ({error}) -> Raising HTTP 400")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(error),
            )

    def patch(
        self, todo_id: str, data: TodoPatchSchema, owner_id: str
    ) -> TodoDTO:
        print(f"[2. CONTROLLER]       TodoController.patch() called for todo_id='{todo_id}'")
        print("[2. CONTROLLER]       Converting TodoPatchSchema -> TodoPatchDTO")
        try:
            request = TodoPatchDTO(
                todo_id=todo_id,
                title=data.title,
                description=data.description,
                completed=data.completed,
            )
            print("[2. CONTROLLER]       Calling Use Case: PatchTodo.execute(...)")
            result = self.patch_todo.execute(request, owner_id)
            print(f"[2. CONTROLLER]       Received patched TodoDTO(id='{result.id}') from Use Case, passing to Route")
            return result
        except TodoRepositoryError:
            print("[2. CONTROLLER]       Caught TodoRepositoryError -> Raising HTTP 503")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Todo storage is temporarily unavailable.",
            )
        except TodoNotFoundError as error:
            print(f"[2. CONTROLLER]       Caught TodoNotFoundError -> Raising HTTP 404")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(error),
            )
        except DomainException as error:
            print(f"[2. CONTROLLER]       Caught DomainException ({error}) -> Raising HTTP 400")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(error),
            )

    def delete(self, todo_id: str, owner_id: str) -> Dict[str, str]:
        print(f"[2. CONTROLLER]       TodoController.delete() called for todo_id='{todo_id}'")
        print("[2. CONTROLLER]       Calling Use Case: DeleteTodo.execute(...)")
        try:
            self.delete_todo.execute(todo_id=todo_id, owner_id=owner_id)
            print(f"[2. CONTROLLER]       Todo deleted successfully, passing response to Route")
            return {"message": "Todo deleted successfully"}
        except TodoRepositoryError:
            print("[2. CONTROLLER]       Caught TodoRepositoryError -> Raising HTTP 503")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Todo storage is temporarily unavailable.",
            )
        except TodoNotFoundError as error:
            print(f"[2. CONTROLLER]       Caught TodoNotFoundError -> Raising HTTP 404")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(error),
            )
        except DomainException as error:
            print(f"[2. CONTROLLER]       Caught DomainException ({error}) -> Raising HTTP 400")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(error),
            )