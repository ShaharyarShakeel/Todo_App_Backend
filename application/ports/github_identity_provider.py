from abc import ABC, abstractmethod

from application.dtos.verified_github_identity import VerifiedGitHubIdentity


class GitHubIdentityProvider(ABC):
    """OAuth boundary for obtaining a verified GitHub user identity."""

    @abstractmethod
    def authorization_url(self, state: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def verify_code(self, code: str) -> VerifiedGitHubIdentity:
        raise NotImplementedError
