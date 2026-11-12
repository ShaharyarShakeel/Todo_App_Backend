"""Represents which database provider is assigned to a user account.

Stores the account's database assignment and its current status.
This entity is independent of the database used to store the assignment.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class AccountAssignment:
    """Maps a public/global user ID to its provider-specific user record."""

    user_id: str
    email_normalized: str
    provider: str
    provider_user_id: str
    status: str = "active"
    google_sub: Optional[str] = None
