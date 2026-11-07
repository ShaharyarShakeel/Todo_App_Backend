import os

from infrastructure.config.env import load_dotenv  # noqa: F401


class PostgresSettings:
    """PostgreSQL connection configuration for the onion architecture."""

    URL = os.getenv("POSTGRES_URL", "")


postgres_settings = PostgresSettings()
