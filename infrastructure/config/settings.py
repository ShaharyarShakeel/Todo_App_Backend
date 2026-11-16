"""Loads environment variables so the application can use its settings."""
import os

from infrastructure.config.env import load_dotenv  # noqa: F401


class Settings:
    """Application and infrastructure configuration loaded from environment variables."""

    DATABASE_PROVIDER: str = os.getenv("DATABASE_PROVIDER", "firebase").strip().lower()
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    )
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    GITHUB_CLIENT_ID: str = os.getenv("GITHUB_CLIENT_ID", "").strip()
    GITHUB_CLIENT_SECRET: str = os.getenv("GITHUB_CLIENT_SECRET", "").strip()
    GITHUB_REDIRECT_URI: str = os.getenv(
        "GITHUB_REDIRECT_URI", "http://localhost:8000/auth/github/callback"
    ).strip()
    RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "").strip()
    RESEND_FROM_EMAIL: str = os.getenv(
        "RESEND_FROM_EMAIL", "onboarding@resend.dev"
    ).strip()
    RESEND_ALLOWED_RECIPIENT: str = os.getenv(
        "RESEND_ALLOWED_RECIPIENT", os.getenv("GMAIL_ADDRESS", "")
    ).strip().lower()
    GMAIL_ADDRESS: str = os.getenv("GMAIL_ADDRESS", "").strip()
    GMAIL_APP_PASSWORD: str = os.getenv("GMAIL_APP_PASSWORD", "").strip()
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.gmail.com").strip()
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    CRON_SECRET: str = os.getenv("CRON_SECRET", "").strip()
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173").strip().rstrip("/")
    DATABASE_SWITCH_PIPE_AUTHKEY: str = os.getenv("DATABASE_SWITCH_PIPE_AUTHKEY", "")
    DATABASE_SWITCH_PIPE_NAME: str = os.getenv(
        "DATABASE_SWITCH_PIPE_NAME", r"\\.\pipe\TodoApiDatabaseSwitch"
    )

    if not JWT_SECRET_KEY:
        raise ValueError("JWT_SECRET_KEY must be set in the environment or .env file.")


settings = Settings()
