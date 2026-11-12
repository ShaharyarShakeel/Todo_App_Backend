import secrets
from uuid import uuid4

from application.dtos.auth_dto import AuthDTO
from application.ports.google_identity_verifier import GoogleIdentityVerifier
from application.exceptions import (
    GoogleAccountLinkRequiredError,
    InvalidCredentialsError,
)
from domain.entities.account_assignment import AccountAssignment
from domain.entities.user import User
from domain.repositories.account_registry import AccountRegistry
from domain.repositories.user_repository import UserRepository


class GoogleSignIn:
    """Verifies Google identity and signs in within the selected provider only."""

    def __init__(
        self,
        registry: AccountRegistry,
        provider_catalog,
        token_service,
        password_hasher,
        identity_verifier: GoogleIdentityVerifier,
    ):
        self.registry = registry
        self.provider_catalog = provider_catalog
        self.token_service = token_service
        self.password_hasher = password_hasher
        self.identity_verifier = identity_verifier

    def execute(self, credential: str) -> AuthDTO:
        identity = self.identity_verifier.verify(credential)
        provider, generation = self.provider_catalog.registration_context()
        assignment = self.registry.get_by_google_sub(identity.subject, provider)

        if assignment is None:
            assignment = self.registry.get_by_email(identity.email, provider)
            if assignment is not None:
                if not identity.email_is_authoritative:
                    raise GoogleAccountLinkRequiredError(
                        "This email already has an account that is not linked to Google. Use email and password."
                    )
                self.registry.set_google_sub(
                    assignment.user_id, provider, identity.subject
                )
                assignment = AccountAssignment(
                    user_id=assignment.user_id,
                    email_normalized=assignment.email_normalized,
                    provider=assignment.provider,
                    provider_user_id=assignment.provider_user_id,
                    status=assignment.status,
                    google_sub=identity.subject,
                )
            else:
                assignment = self._create_google_account(identity, provider)

        if assignment.status != "active":
            raise InvalidCredentialsError("Google account registration is not active.")

        repository: UserRepository = self.provider_catalog.user_repository_for(provider)
        user = repository.get_by_id(assignment.provider_user_id)
        if user is None or user.email.strip().lower() != assignment.email_normalized:
            raise InvalidCredentialsError("Google account is not available in this database.")

        return AuthDTO(
            id=assignment.user_id,
            email=user.email,
            access_token=self.token_service.create_access_token(
                assignment.user_id,
                provider=provider,
                session_generation=generation,
            ),
        )

    def _create_google_account(self, identity, provider: str) -> AccountAssignment:
        repository = self.provider_catalog.user_repository_for(provider)
        assignment = AccountAssignment(
            user_id=str(uuid4()),
            email_normalized=identity.email,
            provider=provider,
            provider_user_id=repository.new_user_id(identity.email),
            status="pending",
            google_sub=identity.subject,
        )
        self.registry.reserve(assignment)

        user = User(
            email=identity.email,
            password_hash=self.password_hasher.hash(secrets.token_urlsafe(48)),
            user_id=assignment.provider_user_id,
        )
        try:
            created_user = repository.create(user)
            if created_user.id != assignment.provider_user_id:
                raise RuntimeError("The provider repository changed the reserved user ID.")
        except Exception:
            try:
                stored_user = repository.get_by_id(assignment.provider_user_id)
                if (
                    stored_user is None
                    or stored_user.email.strip().lower() != identity.email
                ):
                    self.registry.delete_pending(assignment.user_id)
                else:
                    self.registry.activate(assignment.user_id)
            except Exception:
                pass
            raise

        self.registry.activate(assignment.user_id)
        return AccountAssignment(
            user_id=assignment.user_id,
            email_normalized=assignment.email_normalized,
            provider=assignment.provider,
            provider_user_id=assignment.provider_user_id,
            google_sub=assignment.google_sub,
        )
