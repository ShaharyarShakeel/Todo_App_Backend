"""Defines the interface for verifying Google ID tokens.

The application uses this interface to verify a user's Google identity
without depending directly on Google's verification library.
The actual verification is handled by the infrastructure layer.
"""
from abc import ABC, abstractmethod

from application.dtos.verified_google_identity import VerifiedGoogleIdentity


class GoogleIdentityVerifier(ABC):
    """Application port for validating an identity credential issued by Google."""

    @abstractmethod
    def verify(self, credential: str) -> VerifiedGoogleIdentity:
        raise NotImplementedError
