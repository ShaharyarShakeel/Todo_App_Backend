from dataclasses import dataclass


@dataclass(frozen=True)
class VerifiedGitHubIdentity:
    """A GitHub account identity with a verified email address."""

    subject: str
    email: str
