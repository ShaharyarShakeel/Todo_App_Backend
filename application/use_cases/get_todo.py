from domain.exceptions.todo_exceptions import TodoNotFoundError
from domain.repositories.todo_repository import TodoRepository
from application.dtos.todo_dto import TodoDTO


class GetTodo:
    """Use case to retrieve a Todo by ID."""

    def __init__(self, repository: TodoRepository) -> None:
        self.repository = repository

    def execute(self, todo_id: str, owner_id: str) -> TodoDTO:
        print(f"[3. USE CASE]         GetTodo.execute() for todo_id='{todo_id}', owner='{owner_id}'")
        print(f"[3. USE CASE]         Calling Repository Interface: repository.get_by_id(...)")
        todo = self.repository.get_by_id(todo_id, owner_id)
        if not todo:
            print(f"[3. USE CASE]         Todo not found in repository -> Raising TodoNotFoundError")
            raise TodoNotFoundError(f"Todo with ID '{todo_id}' not found.")
        print(f"[3. USE CASE]         Found entity (title='{todo.title}'). Mapping to TodoDTO")
        return TodoDTO(
            id=todo.id,
            title=todo.title,
            description=todo.description,
            completed=todo.completed,
        )