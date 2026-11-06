from application.dtos.auth_dto import AuthDTO
from application.exceptions import InvalidCredentialsError
from domain.repositories.user_repository import UserRepository


class LogIn:
    def __init__(self, repository: UserRepository, password_hasher, token_service):
        self.repository = repository
        self.password_hasher = password_hasher
        self.token_service = token_service

    def execute(self, email: str, password: str) -> AuthDTO:
        user = self.repository.get_by_email(email.strip().lower())
        if user is None or not self.password_hasher.verify(password, user.password_hash):
            raise InvalidCredentialsError("Email or password is incorrect.")

        return AuthDTO(
            id=user.id,
            email=user.email,
           access_token=self.token_service.create_access_token(str(user.id)),
        )
