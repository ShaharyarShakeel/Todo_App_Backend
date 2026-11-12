"""Defines the repository interface for managing account assignments.

Provides methods to reserve, activate, retrieve, and list account
assignments without depending on any specific database implementation.
The infrastructure layer implements these operations.
"""
from abc import ABC, abstractmethod
from typing import List, Optional

from domain.entities.account_assignment import AccountAssignment


class AccountRegistry(ABC):
    """Persistence port for account identity and database assignment metadata."""

    @abstractmethod
    def ensure_indexes(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def reserve(self, assignment: AccountAssignment) -> None:
        """Atomically reserve the unique global ID and normalized email as pending."""
        raise NotImplementedError

    @abstractmethod
    def activate(self, user_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete_pending(self, user_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def add_existing(self, assignment: AccountAssignment) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_by_email(
        self, email_normalized: str, provider: str
    ) -> Optional[AccountAssignment]:
        raise NotImplementedError

    @abstractmethod
    def get_by_google_sub(
        self, google_sub: str, provider: str
    ) -> Optional[AccountAssignment]:
        raise NotImplementedError

    @abstractmethod
    def set_google_sub(self, user_id: str, provider: str, google_sub: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_by_user_id(self, user_id: str) -> Optional[AccountAssignment]:
        raise NotImplementedError

    @abstractmethod
    def get_by_provider_user_id(self, provider_user_id: str) -> List[AccountAssignment]:
        raise NotImplementedError

    @abstractmethod
    def list_all(self) -> List[AccountAssignment]:
        raise NotImplementedError

    @abstractmethod
    def list_pending(self) -> List[AccountAssignment]:
        raise NotImplementedError
