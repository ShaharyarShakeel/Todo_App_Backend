from typing import List

from domain.repositories.todo_repository import TodoRepository
from application.dtos.todo_dto import TodoDTO


class GetAllTodos:
    """Use case to retrieve all Todos."""

    def __init__(self, repository: TodoRepository) -> None:
        self.repository = repository

    def execute(self, owner_id: str) -> List[TodoDTO]:
        print(f"[3. USE CASE]         GetAllTodos.execute() for owner_id='{owner_id}'")
        print(f"[3. USE CASE]         Calling Repository Interface: repository.get_all(...)")
        todos = self.repository.get_all(owner_id)
        print(f"[3. USE CASE]         Repository returned {len(todos)} entities. Mapping to TodoDTOs")
        return [
            TodoDTO(
                id=todo.id,
                title=todo.title,
                description=todo.description,
                completed=todo.completed,
            )
            for todo in todos
        ]