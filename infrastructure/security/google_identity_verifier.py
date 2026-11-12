from google.auth.exceptions import TransportError
from google.auth.transport.requests import Request
from google.oauth2 import id_token

from application.exceptions import (
    GoogleIdentityProviderUnavailableError,
    GoogleSignInConfigurationError,
    InvalidGoogleCredentialError,
)
from application.dtos.verified_google_identity import VerifiedGoogleIdentity
from application.ports.google_identity_verifier import GoogleIdentityVerifier


class GoogleIdentityVerifierAdapter(GoogleIdentityVerifier):
    """Validates Google Identity Services ID tokens against our web client ID."""

    def __init__(self, client_id: str):
        self.client_id = client_id.strip()

    def verify(self, credential: str) -> VerifiedGoogleIdentity:
        if not self.client_id:
            raise GoogleSignInConfigurationError(
                "GOOGLE_CLIENT_ID is not configured on the API."
            )
        if not credential:
            raise InvalidGoogleCredentialError("Google credential is required.")

        try:
            claims = id_token.verify_oauth2_token(
                credential, Request(), audience=self.client_id
            )
        except TransportError as error:
            raise GoogleIdentityProviderUnavailableError(
                "Google identity verification is temporarily unavailable."
            ) from error
        except ValueError as error:
            raise InvalidGoogleCredentialError(
                "Google credential is invalid or expired."
            ) from error

        subject = claims.get("sub")
        email = claims.get("email")
        if not isinstance(subject, str) or not subject:
            raise InvalidGoogleCredentialError("Google credential has no account subject.")
        if not isinstance(email, str) or not email or claims.get("email_verified") is not True:
            raise InvalidGoogleCredentialError(
                "Google must provide an email address verified for this account."
            )

        normalized_email = email.strip().lower()
        is_gmail = normalized_email.endswith("@gmail.com")
        has_workspace_domain = isinstance(claims.get("hd"), str) and bool(claims["hd"])
        return VerifiedGoogleIdentity(
            subject=subject,
            email=normalized_email,
            email_is_authoritative=is_gmail or has_workspace_domain,
        )
