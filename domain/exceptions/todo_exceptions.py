class DomainException(Exception):
    """Base exception for all domain errors."""
    pass


class TodoNotFoundError(DomainException):
    """Raised when a requested Todo is not found."""
    pass


class TodoTitleRequiredError(DomainException):
    """Raised when a Todo title is missing or blank."""
    pass


class TodoTitleTooLongError(DomainException):
    """Raised when a Todo title exceeds the maximum allowed length."""
    pass


class InvalidTodoIdError(DomainException):
    """Raised when a Todo ID format is invalid."""
    pass
