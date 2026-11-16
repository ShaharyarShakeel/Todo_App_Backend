from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import List, Optional

from domain.entities.todo import Todo


class TodoRepository(ABC):
    """
    Todo Repository Interface (Domain Port).
    
    Defines the contract for persistence operations on Todo entities.
    According to Onion Architecture / Clean Architecture, the domain defines
    this interface, and the infrastructure layer implements it.
    """

    @abstractmethod
    def create(self, todo: Todo) -> Todo:
        """Persist a new Todo entity."""
        pass

    @abstractmethod
    def get_all(self, owner_id: str) -> List[Todo]:
        """Retrieve all Todo entities."""
        pass

    @abstractmethod
    def get_by_id(self, todo_id: str, owner_id: str) -> Optional[Todo]:
        """Retrieve a Todo entity by its unique identifier."""
        pass

    @abstractmethod
    def update(self, todo: Todo) -> Optional[Todo]:
        """Update an existing Todo entity."""
        pass

    @abstractmethod
    def delete(self, todo_id: str, owner_id: str) -> bool:
        """Delete a Todo entity by its unique identifier. Returns True if deleted, False otherwise."""
        pass

    @abstractmethod
    def get_unscheduled_reminders(self, limit: int) -> List[Todo]:
        """Find incomplete todos that predate reminder scheduling metadata."""
        pass

    @abstractmethod
    def schedule_reminder(
        self, todo_id: str, due_date: date, reminder_due_at: datetime
    ) -> bool:
        """Set the initial reminder schedule if the due date is still unchanged."""
        pass

    @abstractmethod
    def claim_due_reminders(
        self, now: datetime, lease_until: datetime, claim_id: str, limit: int
    ) -> List[Todo]:
        """Atomically claim due, incomplete, not-yet-sent reminders."""
        pass

    @abstractmethod
    def mark_reminder_sent(
        self,
        todo_id: str,
        reminder_due_at: datetime,
        claim_id: str,
        sent_at: datetime,
    ) -> bool:
        """Mark a reminder sent only while this worker still owns the claim."""
        pass

    @abstractmethod
    def release_reminder_claim(
        self, todo_id: str, reminder_due_at: datetime, claim_id: str
    ) -> bool:
        """Release a failed delivery claim so a later cron run can retry it."""
        pass
