from typing import List, Optional
from uuid import UUID, uuid4

import psycopg

from application.exceptions import TodoRepositoryError
from domain.entities.todo import Todo
from domain.exceptions.todo_exceptions import InvalidTodoIdError
from domain.repositories.todo_repository import TodoRepository
from infrastructure.database.postgres.client import PostgresManager, postgres_manager


class PostgresTodoRepository(TodoRepository):
    """PostgreSQL adapter for the onion architecture's TodoRepository port."""

    def __init__(self, manager: PostgresManager = postgres_manager):
        self.manager = manager

    def create(self, todo: Todo) -> Todo:
        todo_id = str(uuid4())
        try:
            with self.manager.get_connection() as connection:
                connection.execute(
                    "INSERT INTO todos (id, title, description, completed, owner_id) VALUES (%s, %s, %s, %s, %s)",
                    (todo_id, todo.title, todo.description, todo.completed, todo.owner_id),
                )
        except psycopg.Error as error:
            raise TodoRepositoryError("Todo storage operation failed.") from error
        todo.id = todo_id
        return todo

    def get_all(self, owner_id: str) -> List[Todo]:
        try:
            with self.manager.get_connection() as connection:
                rows = connection.execute(
                    "SELECT id, title, description, completed, owner_id FROM todos WHERE owner_id = %s ORDER BY id",
                    (owner_id,),
                ).fetchall()
            return [self._to_domain(row) for row in rows]
        except psycopg.Error as error:
            raise TodoRepositoryError("Todo storage operation failed.") from error

    def get_by_id(self, todo_id: str, owner_id: str) -> Optional[Todo]:
        self._validate_id(todo_id)
        try:
            with self.manager.get_connection() as connection:
                row = connection.execute(
                    "SELECT id, title, description, completed, owner_id FROM todos WHERE id = %s AND owner_id = %s",
                    (todo_id, owner_id),
                ).fetchone()
            return self._to_domain(row) if row else None
        except psycopg.Error as error:
            raise TodoRepositoryError("Todo storage operation failed.") from error

    def update(self, todo: Todo) -> Optional[Todo]:
        self._validate_id(todo.id)
        try:
            with self.manager.get_connection() as connection:
                row = connection.execute(
                    "UPDATE todos SET title = %s, description = %s, completed = %s WHERE id = %s AND owner_id = %s RETURNING id, title, description, completed, owner_id",
                    (todo.title, todo.description, todo.completed, todo.id, todo.owner_id),
                ).fetchone()
            return self._to_domain(row) if row else None
        except psycopg.Error as error:
            raise TodoRepositoryError("Todo storage operation failed.") from error

    def delete(self, todo_id: str, owner_id: str) -> bool:
        self._validate_id(todo_id)
        try:
            with self.manager.get_connection() as connection:
                cursor = connection.execute(
                    "DELETE FROM todos WHERE id = %s AND owner_id = %s",
                    (todo_id, owner_id),
                )
            return cursor.rowcount > 0
        except psycopg.Error as error:
            raise TodoRepositoryError("Todo storage operation failed.") from error

    @staticmethod
    def _validate_id(todo_id: Optional[str]) -> None:
        try:
            UUID(todo_id or "")
        except (ValueError, TypeError, AttributeError) as error:
            raise InvalidTodoIdError(f"Todo ID '{todo_id}' is invalid.") from error

    @staticmethod
    def _to_domain(row) -> Todo:
        return Todo(
            todo_id=row[0],
            title=row[1],
            description=row[2],
            completed=row[3],
            owner_id=row[4],
        )
