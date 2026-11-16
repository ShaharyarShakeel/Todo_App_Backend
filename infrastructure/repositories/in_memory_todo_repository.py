import uuid
from datetime import date, datetime
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
            due_date=todo.due_date,
            reminder_due_at=todo.reminder_due_at,
            reminder_sent_at=todo.reminder_sent_at,
            reminder_claimed_until=todo.reminder_claimed_until,
            reminder_claim_id=todo.reminder_claim_id,
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
                due_date=t.due_date,
                reminder_due_at=t.reminder_due_at,
                reminder_sent_at=t.reminder_sent_at,
                reminder_claimed_until=t.reminder_claimed_until,
                reminder_claim_id=t.reminder_claim_id,
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
            due_date=todo.due_date,
            reminder_due_at=todo.reminder_due_at,
            reminder_sent_at=todo.reminder_sent_at,
            reminder_claimed_until=todo.reminder_claimed_until,
            reminder_claim_id=todo.reminder_claim_id,
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
            due_date=todo.due_date,
            reminder_due_at=todo.reminder_due_at,
            reminder_sent_at=todo.reminder_sent_at,
            reminder_claimed_until=todo.reminder_claimed_until,
            reminder_claim_id=todo.reminder_claim_id,
        )
        return self._todos[todo.id]

    def get_unscheduled_reminders(self, limit: int) -> List[Todo]:
        return [
            todo
            for todo in self.get_all_for_reminders()
            if todo.due_date is not None and todo.reminder_due_at is None
        ][:limit]

    def schedule_reminder(
        self, todo_id: str, due_date: date, reminder_due_at: datetime
    ) -> bool:
        todo = self._todos.get(todo_id)
        if (
            todo is None
            or todo.completed
            or todo.due_date != due_date
            or todo.reminder_due_at is not None
        ):
            return False
        todo.reschedule_reminder(reminder_due_at)
        return True

    def claim_due_reminders(
        self, now: datetime, lease_until: datetime, claim_id: str, limit: int
    ) -> List[Todo]:
        candidates = sorted(
            (
                todo
                for todo in self._todos.values()
                if not todo.completed
                and todo.reminder_due_at is not None
                and todo.reminder_due_at <= now
                and todo.reminder_sent_at is None
                and (
                    todo.reminder_claimed_until is None
                    or todo.reminder_claimed_until <= now
                )
            ),
            key=lambda todo: todo.reminder_due_at,
        )[:limit]
        claimed = []
        for todo in candidates:
            todo.reminder_claimed_until = lease_until
            todo.reminder_claim_id = claim_id
            claimed.append(self._copy(todo))
        return claimed

    def mark_reminder_sent(
        self,
        todo_id: str,
        reminder_due_at: datetime,
        claim_id: str,
        sent_at: datetime,
    ) -> bool:
        todo = self._todos.get(todo_id)
        if not self._owns_claim(todo, reminder_due_at, claim_id) or todo.completed:
            return False
        todo.reminder_sent_at = sent_at
        todo.reminder_claimed_until = None
        todo.reminder_claim_id = None
        return True

    def release_reminder_claim(
        self, todo_id: str, reminder_due_at: datetime, claim_id: str
    ) -> bool:
        todo = self._todos.get(todo_id)
        if not self._owns_claim(todo, reminder_due_at, claim_id):
            return False
        todo.reminder_claimed_until = None
        todo.reminder_claim_id = None
        return True

    def get_all_for_reminders(self) -> List[Todo]:
        return [self._copy(todo) for todo in self._todos.values() if not todo.completed]

    @staticmethod
    def _owns_claim(todo, reminder_due_at: datetime, claim_id: str) -> bool:
        return bool(
            todo
            and todo.reminder_sent_at is None
            and todo.reminder_due_at == reminder_due_at
            and todo.reminder_claim_id == claim_id
        )

    @staticmethod
    def _copy(todo: Todo) -> Todo:
        return Todo(
            todo_id=todo.id,
            title=todo.title,
            description=todo.description,
            completed=todo.completed,
            owner_id=todo.owner_id,
            due_date=todo.due_date,
            reminder_due_at=todo.reminder_due_at,
            reminder_sent_at=todo.reminder_sent_at,
            reminder_claimed_until=todo.reminder_claimed_until,
            reminder_claim_id=todo.reminder_claim_id,
        )

    def delete(self, todo_id: str, owner_id: str) -> bool:
        if todo_id in self._todos and self._todos[todo_id].owner_id == owner_id:
            del self._todos[todo_id]
            return True
        return False
