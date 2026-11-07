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
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173").strip().rstrip("/")

    if not JWT_SECRET_KEY:
        raise ValueError("JWT_SECRET_KEY must be set in the environment or .env file.")


settings = Settings()
