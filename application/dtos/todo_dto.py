from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class TodoCreateDTO:
    title: str
    description: Optional[str] = None


@dataclass(frozen=True)
class TodoUpdateDTO:
    todo_id: str
    title: str
    description: Optional[str]
    completed: bool


@dataclass(frozen=True)
class TodoPatchDTO:
    todo_id: str
    title: Optional[str] = None
    description: Optional[str] = None
    completed: Optional[bool] = None


@dataclass(frozen=True)
class TodoDTO:
    id: Optional[str]
    title: str
    description: Optional[str]
    completed: bool
