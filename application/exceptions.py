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


class GitHubSignInConfigurationError(Exception):
    pass


class InvalidGitHubCredentialError(Exception):
    pass


class GitHubIdentityProviderUnavailableError(Exception):
    pass


class GoogleAccountLinkRequiredError(Exception):
    pass
