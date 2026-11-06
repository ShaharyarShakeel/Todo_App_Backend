from domain.entities.todo import Todo
from domain.repositories.todo_repository import TodoRepository
from application.dtos.todo_dto import TodoCreateDTO, TodoDTO


class CreateTodo:
    """Use case to create a new Todo."""

    def __init__(self, repository: TodoRepository) -> None:
        self.repository = repository

    def execute(self, data: TodoCreateDTO, owner_id: str) -> TodoDTO:
        print(f"[3. USE CASE]         CreateTodo.execute() received title='{data.title}', owner='{owner_id}'")
        print(f"[3. USE CASE]         Instantiating Domain Entity: Todo(...)")
        todo = Todo(
            title=data.title,
            description=data.description,
            completed=False,
            owner_id=owner_id,
        )
        print(f"[3. USE CASE]         Calling Repository Interface: repository.create(todo)")
        created_todo = self.repository.create(todo)
        print(f"[3. USE CASE]         Repository saved entity (ID='{created_todo.id}'). Mapping to TodoDTO")
        return TodoDTO(
            id=created_todo.id,
            title=created_todo.title,
            description=created_todo.description,
            completed=created_todo.completed,
        )
