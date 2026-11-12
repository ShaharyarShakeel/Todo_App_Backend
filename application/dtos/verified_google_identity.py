from dataclasses import dataclass


@dataclass(frozen=True)
class VerifiedGoogleIdentity:
    """Verified Google claims passed from the identity adapter to the use case."""

    subject: str
    email: str
    email_is_authoritative: bool
