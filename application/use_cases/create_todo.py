from domain.entities.todo import Todo
from domain.repositories.todo_repository import TodoRepository
from application.dtos.todo_dto import TodoCreateDTO, TodoDTO
from application.services.todo_reminder_scheduler import calculate_reminder_due_at


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
            due_date=data.due_date,
            reminder_due_at=(
                calculate_reminder_due_at(data.due_date)
                if data.due_date is not None
                else None
            ),
        )
        print(f"[3. USE CASE]         Calling Repository Interface: repository.create(todo)")
        created_todo = self.repository.create(todo)
        print(f"[3. USE CASE]         Repository saved entity (ID='{created_todo.id}'). Mapping to TodoDTO")
        return TodoDTO(
            id=created_todo.id,
            title=created_todo.title,
            description=created_todo.description,
            completed=created_todo.completed,
            due_date=created_todo.due_date,
        )
