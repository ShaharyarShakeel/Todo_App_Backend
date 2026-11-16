import logging
from urllib.parse import urlencode

import requests

from application.dtos.verified_github_identity import VerifiedGitHubIdentity
from application.exceptions import (
    GitHubIdentityProviderUnavailableError,
    GitHubSignInConfigurationError,
    InvalidGitHubCredentialError,
)
from application.ports.github_identity_provider import GitHubIdentityProvider

logger = logging.getLogger(__name__)


class GitHubOAuthClient(GitHubIdentityProvider):
    """Exchanges GitHub OAuth codes and resolves the user's verified email."""

    AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
    TOKEN_URL = "https://github.com/login/oauth/access_token"
    API_URL = "https://api.github.com"

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id.strip()
        self.client_secret = client_secret.strip()
        self.redirect_uri = redirect_uri.strip()

    def authorization_url(self, state: str) -> str:
        self._ensure_configured()
        query = urlencode(
            {
                "client_id": self.client_id,
                "redirect_uri": self.redirect_uri,
                "scope": "read:user user:email",
                "state": state,
            }
        )
        return f"{self.AUTHORIZE_URL}?{query}"

    def verify_code(self, code: str) -> VerifiedGitHubIdentity:
        self._ensure_configured()
        if not code:
            raise InvalidGitHubCredentialError("GitHub authorization code is missing.")

        try:
            token_response = requests.post(
                self.TOKEN_URL,
                headers={"Accept": "application/json"},
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": self.redirect_uri,
                },
                timeout=10,
            )
            if token_response.status_code >= 500:
                raise GitHubIdentityProviderUnavailableError(
                    "GitHub sign-in is temporarily unavailable."
                )
            token_payload = token_response.json()
            provider_error = token_payload.get("error")
            if provider_error:
                # GitHub error payloads do not contain the submitted code or secret.
                logger.warning(
                    "GitHub OAuth token exchange rejected with error=%s",
                    provider_error,
                )
                if provider_error == "incorrect_client_credentials":
                    raise GitHubSignInConfigurationError(
                        "GitHub rejected the client credentials. Confirm the client ID "
                        "and secret belong to the same OAuth App."
                    )
                if provider_error == "redirect_uri_mismatch":
                    raise GitHubSignInConfigurationError(
                        "GITHUB_REDIRECT_URI does not match the OAuth App callback URL."
                    )
                if provider_error == "unverified_user_email":
                    raise InvalidGitHubCredentialError(
                        "Verify your primary email address in GitHub, then try again."
                    )
                if provider_error == "bad_verification_code":
                    raise InvalidGitHubCredentialError(
                        "GitHub rejected this expired or already-used code. Start a new "
                        "sign-in attempt and complete it once."
                    )
                raise InvalidGitHubCredentialError(
                    f"GitHub rejected the token exchange ({provider_error})."
                )

            token_response.raise_for_status()
            access_token = token_payload.get("access_token")
            if not isinstance(access_token, str) or not access_token:
                raise InvalidGitHubCredentialError(
                    "GitHub returned no access token. Check the API logs for the "
                    "provider error code."
                )

            headers = {
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {access_token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "Todo-App",
            }
            profile_response = requests.get(
                f"{self.API_URL}/user", headers=headers, timeout=10
            )
            profile_response.raise_for_status()
            profile = profile_response.json()
            subject = profile.get("id")
            if subject is None:
                raise InvalidGitHubCredentialError(
                    "GitHub profile has no stable account ID."
                )

            email_response = requests.get(
                f"{self.API_URL}/user/emails", headers=headers, timeout=10
            )
            email_response.raise_for_status()
            email_records = email_response.json()
            selected = next(
                (
                    item
                    for item in email_records
                    if item.get("primary") and item.get("verified")
                ),
                None,
            )
            email = selected.get("email") if selected else None

            if not isinstance(email, str) or not email.strip():
                raise InvalidGitHubCredentialError(
                    "GitHub must provide a verified email address."
                )
            return VerifiedGitHubIdentity(
                subject=str(subject), email=email.strip().lower()
            )
        except (
            GitHubIdentityProviderUnavailableError,
            GitHubSignInConfigurationError,
            InvalidGitHubCredentialError,
        ):
            raise
        except requests.Timeout as error:
            raise GitHubIdentityProviderUnavailableError(
                "GitHub sign-in timed out. Please try again."
            ) from error
        except requests.RequestException as error:
            raise GitHubIdentityProviderUnavailableError(
                "GitHub sign-in is temporarily unavailable."
            ) from error
        except (ValueError, TypeError) as error:
            raise InvalidGitHubCredentialError(
                "GitHub returned an invalid identity response."
            ) from error

    def _ensure_configured(self) -> None:
        if not self.client_id or not self.client_secret or not self.redirect_uri:
            raise GitHubSignInConfigurationError(
                "GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET, and GITHUB_REDIRECT_URI "
                "must be configured on the API."
            )
