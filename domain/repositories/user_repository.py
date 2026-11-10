from abc import ABC, abstractmethod
from typing import List, Optional

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

    @abstractmethod
    def list_users(self) -> List[User]:
        """List persisted users for safe account-registry backfill."""
        raise NotImplementedError

    @abstractmethod
    def new_user_id(self, email: str) -> str:
        """Generate an ID in this provider's native user-ID format."""
        raise NotImplementedError
