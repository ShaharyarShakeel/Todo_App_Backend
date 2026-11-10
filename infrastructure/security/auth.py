"""Provides password hashing and JWT access token management."""
import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt

from infrastructure.config.settings import settings


class PasswordHasher:
    ITERATIONS = 600_000

    def hash(self, password: str) -> str:
        salt = secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, self.ITERATIONS)
        salt_text = base64.urlsafe_b64encode(salt).decode()
        digest_text = base64.urlsafe_b64encode(digest).decode()
        return f"pbkdf2_sha256${self.ITERATIONS}${salt_text}${digest_text}"

    def verify(self, password: str, password_hash: str) -> bool:
        try:
            algorithm, iterations, salt_text, digest_text = password_hash.split("$", 3)
            if algorithm != "pbkdf2_sha256":
                return False
            salt = base64.urlsafe_b64decode(salt_text.encode())
            expected_digest = base64.urlsafe_b64decode(digest_text.encode())
            actual_digest = hashlib.pbkdf2_hmac(
                "sha256", password.encode(), salt, int(iterations)
            )
            return hmac.compare_digest(actual_digest, expected_digest)
        except (ValueError, TypeError):
            return False


class TokenService:
    def create_access_token(
        self,
        subject: str,
        provider: Optional[str] = None,
        session_generation: Optional[int] = None,
    ) -> str:
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )
        payload = {"sub": subject, "exp": expires_at}
        if provider is not None:
            payload["provider"] = provider
        if session_generation is not None:
            payload["session_generation"] = session_generation
        return jwt.encode(
            payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )

    def get_subject(self, token: str) -> Optional[str]:
        payload = self.get_claims(token)
        subject = payload.get("sub") if payload else None
        return subject if isinstance(subject, str) else None

    def get_claims(self, token: str) -> Optional[dict]:
        try:
            return jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
        except jwt.InvalidTokenError:
            return None
