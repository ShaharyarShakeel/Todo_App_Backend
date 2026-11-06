from domain.exceptions.todo_exceptions import TodoNotFoundError
from domain.repositories.todo_repository import TodoRepository
from application.dtos.todo_dto import TodoDTO, TodoPatchDTO


class PatchTodo:
    """Use case to partially update an existing Todo."""

    def __init__(self, repository: TodoRepository) -> None:
        self.repository = repository

    def execute(self, data: TodoPatchDTO, owner_id: str) -> TodoDTO:
        print(f"[3. USE CASE]         PatchTodo.execute() for todo_id='{data.todo_id}', owner='{owner_id}'")
        print(f"[3. USE CASE]         Fetching existing Todo from Repository...")
        todo = self.repository.get_by_id(data.todo_id, owner_id)
        if not todo:
            print(f"[3. USE CASE]         Todo not found in repository -> Raising TodoNotFoundError")
            raise TodoNotFoundError(f"Todo with ID '{data.todo_id}' not found.")

        print(f"[3. USE CASE]         Applying partial updates to Domain Entity...")
        if data.title is not None:
            todo.update_title(data.title)

        if data.description is not None:
            todo.update_description(data.description)

        if data.completed is not None:
            if data.completed:
                todo.mark_completed()
            else:
                todo.mark_incomplete()

        print(f"[3. USE CASE]         Persisting patched Todo via repository.update(...)")
        updated_todo = self.repository.update(todo)
        if not updated_todo:
            print(f"[3. USE CASE]         Repository update returned None -> Raising TodoNotFoundError")
            raise TodoNotFoundError(
                f"Todo with ID '{data.todo_id}' could not be updated."
            )

        print(f"[3. USE CASE]         Patch persisted. Mapping to TodoDTO")
        return TodoDTO(
            id=updated_todo.id,
            title=updated_todo.title,
            description=updated_todo.description,
            completed=updated_todo.completed,
        )
