from dataclasses import dataclass


@dataclass(frozen=True)
class AccountAssignment:
    """Maps a public/global user ID to its provider-specific user record."""

    user_id: str
    email_normalized: str
    provider: str
    provider_user_id: str
    status: str = "active"
