from application.dtos.auth_dto import AuthDTO
from application.exceptions import UserAlreadyExistsError
from domain.entities.user import User
from domain.repositories.user_repository import UserRepository


class SignUp:
    def __init__(self, repository: UserRepository, password_hasher, token_service):
        self.repository = repository
        self.password_hasher = password_hasher
        self.token_service = token_service

    def execute(self, email: str, password: str) -> AuthDTO:
        normalized_email = email.strip().lower()
        if self.repository.get_by_email(normalized_email) is not None:
            raise UserAlreadyExistsError("An account with this email already exists.")

        user = User(
            email=normalized_email,
            password_hash=self.password_hasher.hash(password),
        )
        created_user = self.repository.create(user)
        return AuthDTO(
            id=created_user.id,
            email=created_user.email,
            access_token=self.token_service.create_access_token(str(created_user.id)),
        )
