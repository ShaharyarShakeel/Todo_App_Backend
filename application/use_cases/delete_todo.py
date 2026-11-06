from domain.exceptions.todo_exceptions import TodoNotFoundError
from domain.repositories.todo_repository import TodoRepository


class DeleteTodo:
    """Use case to delete a Todo by ID."""

    def __init__(self, repository: TodoRepository) -> None:
        self.repository = repository

    def execute(self, todo_id: str, owner_id: str) -> bool:
        print(f"[3. USE CASE]         DeleteTodo.execute() for todo_id='{todo_id}', owner='{owner_id}'")
        print(f"[3. USE CASE]         Calling Repository Interface: repository.delete(...)")
        deleted = self.repository.delete(todo_id, owner_id)
        if not deleted:
            print(f"[3. USE CASE]         Todo not found or not deleted -> Raising TodoNotFoundError")
            raise TodoNotFoundError(f"Todo with ID '{todo_id}' not found.")
        print(f"[3. USE CASE]         Todo deleted successfully from repository")
        return True