from abc import ABC, abstractmethod
from typing import Optional

from domain.entities.user import User


class UserRepository(ABC):
    @abstractmethod
    def create(self, user: User) -> User:
        raise NotImplementedError

    @abstractmethod
    def get_by_email(self, email: str) -> Optional[User]:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, user_id: str) -> Optional[User]:
        """Retrieve a persisted user by the identifier used in access tokens."""
        raise NotImplementedError
