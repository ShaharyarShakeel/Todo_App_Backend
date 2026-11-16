from datetime import date, datetime
from typing import Optional

from domain.value_objects import TodoDescription, TodoTitle


class Todo:
    """
    Todo Domain Entity.
    
    Represents the core business object in the domain.
    Encapsulates state, business rules, and invariants.
    """
    MAX_TITLE_LENGTH = TodoTitle.MAX_LENGTH

    def __init__(
        self,
        title: str,
        description: Optional[str] = None,
        completed: bool = False,
        todo_id: Optional[str] = None,
        owner_id: Optional[str] = None,
        due_date: Optional[date] = None,
        reminder_due_at: Optional[datetime] = None,
        reminder_sent_at: Optional[datetime] = None,
        reminder_claimed_until: Optional[datetime] = None,
        reminder_claim_id: Optional[str] = None,
    ):
        self.id = todo_id
        self.owner_id = owner_id
        self._title = TodoTitle(title)
        self._description = TodoDescription(description) if description else None
        self.completed = completed
        self.due_date = due_date
        self.reminder_due_at = reminder_due_at
        self.reminder_sent_at = reminder_sent_at
        self.reminder_claimed_until = reminder_claimed_until
        self.reminder_claim_id = reminder_claim_id
        print(f"[4. DOMAIN ENTITY]    Todo entity created | title='{self.title}', owner='{self.owner_id}', completed={self.completed}")

    @property
    def title(self) -> str:
        return self._title.value

    @property
    def description(self) -> Optional[str]:
        return self._description.value if self._description is not None else None

    def mark_completed(self) -> None:
        """Domain behavior: Mark the todo as completed."""
        self.completed = True
        print("[4. DOMAIN ENTITY]    Todo marked completed")

    def mark_incomplete(self) -> None:
        """Domain behavior: Mark the todo as incomplete."""
        self.completed = False
        print("[4. DOMAIN ENTITY]    Todo marked incomplete")

    def update_title(self, new_title: str) -> None:
        """Domain behavior: Update title enforcing domain rules."""
        self._title = TodoTitle(new_title)
        print(f"[4. DOMAIN ENTITY]    Todo title updated to '{self.title}'")

    def update_description(self, new_description: Optional[str]) -> None:
        """Domain behavior: Update description."""
        self._description = (
            TodoDescription(new_description) if new_description else None
        )
        print(f"[4. DOMAIN ENTITY]    Todo description updated")

    def update_due_date(self, new_due_date: date) -> None:
        """Update the Todo's due date."""
        self.due_date = new_due_date

    def reschedule_reminder(self, reminder_due_at: Optional[datetime]) -> None:
        """Reset delivery tracking after a due-date change."""
        self.reminder_due_at = reminder_due_at
        self.reminder_sent_at = None
        self.reminder_claimed_until = None
        self.reminder_claim_id = None

    def update(
        self,
        title: str,
        description: Optional[str] = None,
        completed: Optional[bool] = None,
        due_date: Optional[date] = None,
    ) -> None:
        """Domain behavior: Update all details enforcing domain invariants."""
        self.update_title(title)
        self.update_description(description)
        if completed is not None:
            self.completed = completed
        if due_date is not None:
            self.update_due_date(due_date)
        print(f"[4. DOMAIN ENTITY]    Todo fully updated | title='{self.title}', completed={self.completed}")
