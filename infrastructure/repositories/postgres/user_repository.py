from typing import List, Optional
from uuid import uuid4

import psycopg
from psycopg.errors import UniqueViolation

from application.exceptions import UserAlreadyExistsError, UserRepositoryError
from domain.entities.user import User
from domain.repositories.user_repository import UserRepository
from infrastructure.database.postgres.client import PostgresManager, postgres_manager


class PostgresUserRepository(UserRepository):
    """PostgreSQL adapter for the onion architecture's UserRepository port."""

    def __init__(self, manager: PostgresManager = postgres_manager):
        self.manager = manager

    def ensure_indexes(self) -> None:
        # The users.email UNIQUE constraint is created with the table.
        return None

    def create(self, user: User) -> User:
        user_id = user.id or str(uuid4())
        try:
            with self.manager.get_connection() as connection:
                connection.execute(
                    "INSERT INTO users (id, email, password_hash) VALUES (%s, %s, %s)",
                    (user_id, user.email.strip().lower(), user.password_hash),
                )
        except UniqueViolation as error:
            raise UserAlreadyExistsError("An account with this email already exists.") from error
        except psycopg.Error as error:
            raise UserRepositoryError("User storage operation failed.") from error
        user.id = user_id
        return user

    def get_by_email(self, email: str) -> Optional[User]:
        try:
            with self.manager.get_connection() as connection:
                row = connection.execute(
                    "SELECT id, email, password_hash FROM users WHERE email = %s",
                    (email.strip().lower(),),
                ).fetchone()
        except psycopg.Error as error:
            raise UserRepositoryError("User storage operation failed.") from error
        if row is None:
            return None
        return User(user_id=row[0], email=row[1], password_hash=row[2])

    def get_by_id(self, user_id: str) -> Optional[User]:
        try:
            with self.manager.get_connection() as connection:
                row = connection.execute(
                    "SELECT id, email, password_hash FROM users WHERE id = %s",
                    (user_id,),
                ).fetchone()
        except psycopg.Error as error:
            raise UserRepositoryError("User storage operation failed.") from error
        if row is None:
            return None
        return User(user_id=row[0], email=row[1], password_hash=row[2])

    def new_user_id(self, email: str) -> str:
        return str(uuid4())

    def list_users(self) -> List[User]:
        try:
            with self.manager.get_connection() as connection:
                rows = connection.execute(
                    "SELECT id, email, password_hash FROM users"
                ).fetchall()
        except psycopg.Error as error:
            raise UserRepositoryError("User storage operation failed.") from error
        return [User(user_id=row[0], email=row[1], password_hash=row[2]) for row in rows]
