from abc import ABC, abstractmethod
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