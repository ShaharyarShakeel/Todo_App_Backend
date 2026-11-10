class TodoRepositoryError(Exception):
    pass


class UserRepositoryError(Exception):
    pass


class AccountRegistryConflictError(Exception):
    pass


class UserAlreadyExistsError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass
