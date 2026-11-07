import psycopg
from psycopg import Connection

from infrastructure.config.postgres_settings import postgres_settings


class PostgresManager:
    """Connects to PostgreSQL and initializes the onion API's tables."""

    def __init__(self, dsn: str = postgres_settings.URL):
        self.dsn = dsn

    def connect(self) -> None:
        if not self.dsn:
            raise ValueError("POSTGRES_URL must be configured in the environment or .env file.")
        try:
            with psycopg.connect(self.dsn) as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    cursor.execute(
                        """
                        CREATE TABLE IF NOT EXISTS users (
                            id TEXT PRIMARY KEY,
                            email TEXT NOT NULL UNIQUE,
                            password_hash TEXT NOT NULL
                        )
                        """
                    )
                    cursor.execute(
                        """
                        CREATE TABLE IF NOT EXISTS todos (
                            id TEXT PRIMARY KEY,
                            title TEXT NOT NULL,
                            description TEXT,
                            completed BOOLEAN NOT NULL DEFAULT FALSE,
                            owner_id TEXT NOT NULL,
                            CONSTRAINT fk_todos_owner_id_users
                                FOREIGN KEY (owner_id) REFERENCES users (id)
                        )
                        """
                    )
                    cursor.execute(
                        """
                        CREATE INDEX IF NOT EXISTS idx_todos_owner_id ON todos (owner_id)
                        """
                    )

                    # CREATE TABLE IF NOT EXISTS leaves an older todos table unchanged.
                    # Add and validate the FK separately so existing data is preserved.
                    cursor.execute(
                        """
                        SELECT pg_get_constraintdef(oid), convalidated
                        FROM pg_constraint
                        WHERE conrelid = 'todos'::regclass
                          AND conname = 'fk_todos_owner_id_users'
                        """
                    )
                    foreign_key = cursor.fetchone()
                    if foreign_key is None:
                        cursor.execute(
                            """
                            ALTER TABLE todos
                            ADD CONSTRAINT fk_todos_owner_id_users
                            FOREIGN KEY (owner_id) REFERENCES users (id)
                            NOT VALID
                            """
                        )
                        is_validated = False
                    else:
                        definition, is_validated = foreign_key
                        if "FOREIGN KEY (owner_id) REFERENCES users(id)" not in definition:
                            raise RuntimeError(
                                "Constraint fk_todos_owner_id_users exists with an unexpected definition."
                            )

                    if not is_validated:
                        cursor.execute(
                            "ALTER TABLE todos VALIDATE CONSTRAINT fk_todos_owner_id_users"
                        )
            print("PostgreSQL connected successfully")
        except psycopg.Error as error:
            print(f"PostgreSQL connection failed: {error}")
            raise

    def get_connection(self) -> Connection:
        if not self.dsn:
            raise ValueError("POSTGRES_URL must be configured in the environment or .env file.")
        return psycopg.connect(self.dsn)

    def close(self) -> None:
        # Each repository operation uses a short-lived context-managed connection.
        pass


postgres_manager = PostgresManager()


def connect_to_postgres() -> None:
    postgres_manager.connect()


def close_postgres() -> None:
    postgres_manager.close()
