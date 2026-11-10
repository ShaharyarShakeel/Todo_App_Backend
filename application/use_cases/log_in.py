from application.dtos.auth_dto import AuthDTO
from application.exceptions import InvalidCredentialsError
from domain.repositories.user_repository import UserRepository


class LogIn:
    def __init__(
        self,
        repository: UserRepository,
        password_hasher,
        token_service,
        account_registry=None,
        provider_catalog=None,
    ):
        self.repository = repository
        self.password_hasher = password_hasher
        self.token_service = token_service
        self.account_registry = account_registry
        self.provider_catalog = provider_catalog

    def execute(self, email: str, password: str) -> AuthDTO:
        if self.account_registry is not None and self.provider_catalog is not None:
            normalized_email = email.strip().lower()
            provider, session_generation = self.provider_catalog.registration_context()
            assignment = self.account_registry.get_by_email(normalized_email, provider)
            if assignment is None or assignment.status != "active":
                raise InvalidCredentialsError("Email or password is incorrect.")
            repository = self.provider_catalog.user_repository_for(assignment.provider)
            user = repository.get_by_id(assignment.provider_user_id)
            if (
                user is None
                or user.email.strip().lower() != assignment.email_normalized
                or not self.password_hasher.verify(password, user.password_hash)
            ):
                raise InvalidCredentialsError("Email or password is incorrect.")
            return AuthDTO(
                id=assignment.user_id,
                email=user.email,
                access_token=self.token_service.create_access_token(
                    assignment.user_id,
                    provider=assignment.provider,
                    session_generation=session_generation,
                ),
            )

        user = self.repository.get_by_email(email.strip().lower())
        if user is None or not self.password_hasher.verify(password, user.password_hash):
            raise InvalidCredentialsError("Email or password is incorrect.")

        return AuthDTO(
            id=user.id,
            email=user.email,
           access_token=self.token_service.create_access_token(str(user.id)),
        )
