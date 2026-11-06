from dataclasses import dataclass
from typing import ClassVar

from domain.exceptions.todo_exceptions import (
    TodoTitleRequiredError,
    TodoTitleTooLongError,
)


@dataclass(frozen=True)
class TodoTitle:
    value: str

    MAX_LENGTH: ClassVar[int] = 200

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise TodoTitleRequiredError("Title is required and cannot be empty.")

        normalized_title = self.value.strip()
        if len(normalized_title) > self.MAX_LENGTH:
            raise TodoTitleTooLongError(
                f"Title cannot exceed {self.MAX_LENGTH} characters."
            )

        object.__setattr__(self, "value", normalized_title)
