import uuid
from typing import Dict, List, Optional

from domain.entities.todo import Todo
from domain.repositories.todo_repository import TodoRepository


class InMemoryTodoRepository(TodoRepository):
    """
    In-memory implementation of the TodoRepository interface.
    
    Ideal for unit testing application use cases without requiring a MongoDB instance.
    Demonstrates pure Dependency Inversion in Onion Architecture.
    """

    def __init__(self, initial_todos: Optional[List[Todo]] = None):
        self._todos: Dict[str, Todo] = {}
        if initial_todos:
            for todo in initial_todos:
                todo_id = todo.id or str(uuid.uuid4())
                todo.id = todo_id
                self._todos[todo_id] = todo

    def create(self, todo: Todo) -> Todo:
        todo_id = todo.id or str(uuid.uuid4())
        todo.id = todo_id
        # Store a copy or state
        self._todos[todo_id] = Todo(
            todo_id=todo.id,
            title=todo.title,
            description=todo.description,
            completed=todo.completed,
            owner_id=todo.owner_id,
        )
        return self._todos[todo_id]

    def get_all(self, owner_id: str) -> List[Todo]:
        return [
            Todo(
                todo_id=t.id,
                title=t.title,
                description=t.description,
                completed=t.completed,
                owner_id=t.owner_id,
            )
            for t in self._todos.values()
            if t.owner_id == owner_id
        ]

    def get_by_id(self, todo_id: str, owner_id: str) -> Optional[Todo]:
        todo = self._todos.get(todo_id)
        if not todo or todo.owner_id != owner_id:
            return None
        return Todo(
            todo_id=todo.id,
            title=todo.title,
            description=todo.description,
            completed=todo.completed,
            owner_id=todo.owner_id,
        )

    def update(self, todo: Todo) -> Optional[Todo]:
        if (
            not todo.id
            or todo.id not in self._todos
            or self._todos[todo.id].owner_id != todo.owner_id
        ):
            return None
        self._todos[todo.id] = Todo(
            todo_id=todo.id,
            title=todo.title,
            description=todo.description,
            completed=todo.completed,
            owner_id=todo.owner_id,
        )
        return self._todos[todo.id]

    def delete(self, todo_id: str, owner_id: str) -> bool:
        if todo_id in self._todos and self._todos[todo_id].owner_id == owner_id:
            del self._todos[todo_id]
            return True
        return False
