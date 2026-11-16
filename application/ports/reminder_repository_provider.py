from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List

from domain.repositories.todo_repository import TodoRepository
from domain.repositories.user_repository import UserRepository


@dataclass(frozen=True)
class ReminderRepositories:
    todos: TodoRepository
    users: UserRepository


class ReminderRepositoryProvider(ABC):
    """Provides repositories for the database providers active in this process."""

    @abstractmethod
    def active_reminder_repositories(self) -> List[ReminderRepositories]:
        raise NotImplementedError
