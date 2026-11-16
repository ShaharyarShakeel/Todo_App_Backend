from abc import ABC, abstractmethod
from datetime import date


class EmailSender(ABC):
    """Application port for sending account-related email."""

    @abstractmethod
    def send_welcome_email(self, email: str) -> None:
        """Send the account welcome message to the given address."""
        raise NotImplementedError

    @abstractmethod
    def send_todo_reminder_email(
        self, email: str, title: str, due_date: date
    ) -> None:
        """Send a Gmail reminder about a Todo due date."""
        raise NotImplementedError
