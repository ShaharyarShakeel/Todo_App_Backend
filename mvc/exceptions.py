class InvalidTodoIdError(ValueError):
    pass


class TodoStorageError(Exception):
    pass


class UserStorageError(Exception):
    pass


class UserAlreadyExistsError(Exception):
    pass
