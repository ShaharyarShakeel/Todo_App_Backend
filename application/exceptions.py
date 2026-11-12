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


class InvalidGoogleCredentialError(Exception):
    pass


class GoogleSignInConfigurationError(Exception):
    pass


class GoogleIdentityProviderUnavailableError(Exception):
    pass


class GoogleAccountLinkRequiredError(Exception):
    pass
