from application.dtos.auth_dto import AuthDTO
from application.exceptions import UserAlreadyExistsError
from domain.entities.account_assignment import AccountAssignment
from domain.entities.user import User
from domain.repositories.account_registry import AccountRegistry
from domain.repositories.user_repository import UserRepository
from uuid import uuid4


class SignUp:
    def __init__(
        self,
        repository: UserRepository,
        password_hasher,
        token_service,
        account_registry: AccountRegistry = None,
        provider_catalog=None,
    ):
        self.repository = repository
        self.password_hasher = password_hasher
        self.token_service = token_service
        self.account_registry = account_registry
        self.provider_catalog = provider_catalog

    def execute(self, email: str, password: str) -> AuthDTO:
        normalized_email = email.strip().lower()
        if self.account_registry is not None and self.provider_catalog is not None:
            return self._execute_registered(normalized_email, password)

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

    def _execute_registered(self, normalized_email: str, password: str) -> AuthDTO:
        provider, session_generation = self.provider_catalog.registration_context()
        repository = self.provider_catalog.user_repository_for(provider)
        user_id = str(uuid4())
        provider_user_id = repository.new_user_id(normalized_email)
        password_hash = self.password_hasher.hash(password)
        assignment = AccountAssignment(
            user_id=user_id,
            email_normalized=normalized_email,
            provider=provider,
            provider_user_id=provider_user_id,
            status="pending",
        )
        self.account_registry.reserve(assignment)

        user = User(
            email=normalized_email,
            password_hash=password_hash,
            user_id=provider_user_id,
        )
        try:
            created_user = repository.create(user)
            if created_user.id != provider_user_id:
                raise RuntimeError("The provider repository changed the reserved user ID.")
        except Exception:
            # If the database outcome was ambiguous, retain the pending entry for
            # startup recovery rather than risking an unregistered user account.
            try:
                stored_user = repository.get_by_id(provider_user_id)
                if (
                    stored_user is None
                    or stored_user.email.strip().lower() != normalized_email
                ):
                    self.account_registry.delete_pending(user_id)
                else:
                    self.account_registry.activate(user_id)
            except Exception:
                pass
            raise

        self.account_registry.activate(user_id)
        return AuthDTO(
            id=user_id,
            email=user.email,
            access_token=self.token_service.create_access_token(
                user_id, provider=provider, session_generation=session_generation
            ),
        )
