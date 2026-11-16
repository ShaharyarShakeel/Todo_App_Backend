from datetime import date, datetime
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
                    "INSERT INTO todos (id, title, description, completed, due_date, reminder_due_at, reminder_sent_at, reminder_claimed_until, reminder_claim_id, owner_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (
                        todo_id,
                        todo.title,
                        todo.description,
                        todo.completed,
                        todo.due_date,
                        todo.reminder_due_at,
                        todo.reminder_sent_at,
                        todo.reminder_claimed_until,
                        todo.reminder_claim_id,
                        todo.owner_id,
                    ),
                )
        except psycopg.Error as error:
            raise TodoRepositoryError("Todo storage operation failed.") from error
        todo.id = todo_id
        return todo

    def get_all(self, owner_id: str) -> List[Todo]:
        try:
            with self.manager.get_connection() as connection:
                rows = connection.execute(
                    "SELECT id, title, description, completed, due_date, owner_id, reminder_due_at, reminder_sent_at, reminder_claimed_until, reminder_claim_id FROM todos WHERE owner_id = %s ORDER BY id",
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
                    "SELECT id, title, description, completed, due_date, owner_id, reminder_due_at, reminder_sent_at, reminder_claimed_until, reminder_claim_id FROM todos WHERE id = %s AND owner_id = %s",
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
                    "UPDATE todos SET title = %s, description = %s, completed = %s, due_date = %s, reminder_due_at = %s, reminder_sent_at = %s, reminder_claimed_until = %s, reminder_claim_id = %s WHERE id = %s AND owner_id = %s RETURNING id, title, description, completed, due_date, owner_id, reminder_due_at, reminder_sent_at, reminder_claimed_until, reminder_claim_id",
                    (
                        todo.title,
                        todo.description,
                        todo.completed,
                        todo.due_date,
                        todo.reminder_due_at,
                        todo.reminder_sent_at,
                        todo.reminder_claimed_until,
                        todo.reminder_claim_id,
                        todo.id,
                        todo.owner_id,
                    ),
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

    def get_unscheduled_reminders(self, limit: int) -> List[Todo]:
        try:
            with self.manager.get_connection() as connection:
                rows = connection.execute(
                    "SELECT id, title, description, completed, due_date, owner_id, reminder_due_at, reminder_sent_at, reminder_claimed_until, reminder_claim_id FROM todos WHERE completed = FALSE AND due_date IS NOT NULL AND reminder_due_at IS NULL ORDER BY due_date LIMIT %s",
                    (limit,),
                ).fetchall()
            return [self._to_domain(row) for row in rows]
        except psycopg.Error as error:
            raise TodoRepositoryError("Todo storage operation failed.") from error

    def schedule_reminder(
        self, todo_id: str, due_date: date, reminder_due_at: datetime
    ) -> bool:
        self._validate_id(todo_id)
        try:
            with self.manager.get_connection() as connection:
                cursor = connection.execute(
                    "UPDATE todos SET reminder_due_at = %s, reminder_sent_at = NULL, reminder_claimed_until = NULL, reminder_claim_id = NULL WHERE id = %s AND due_date = %s AND completed = FALSE AND reminder_due_at IS NULL",
                    (reminder_due_at, todo_id, due_date),
                )
            return cursor.rowcount > 0
        except psycopg.Error as error:
            raise TodoRepositoryError("Todo storage operation failed.") from error

    def claim_due_reminders(
        self, now: datetime, lease_until: datetime, claim_id: str, limit: int
    ) -> List[Todo]:
        try:
            with self.manager.get_connection() as connection:
                rows = connection.execute(
                    """
                    WITH due AS (
                        SELECT id
                        FROM todos
                        WHERE completed = FALSE
                          AND reminder_due_at <= %s
                          AND reminder_sent_at IS NULL
                          AND (reminder_claimed_until IS NULL OR reminder_claimed_until <= %s)
                        ORDER BY reminder_due_at
                        LIMIT %s
                        FOR UPDATE SKIP LOCKED
                    )
                    UPDATE todos AS todo
                    SET reminder_claimed_until = %s, reminder_claim_id = %s
                    FROM due
                    WHERE todo.id = due.id
                    RETURNING todo.id, todo.title, todo.description, todo.completed,
                              todo.due_date, todo.owner_id, todo.reminder_due_at,
                              todo.reminder_sent_at, todo.reminder_claimed_until,
                              todo.reminder_claim_id
                    """,
                    (now, now, limit, lease_until, claim_id),
                ).fetchall()
            return [self._to_domain(row) for row in rows]
        except psycopg.Error as error:
            raise TodoRepositoryError("Todo storage operation failed.") from error

    def mark_reminder_sent(
        self,
        todo_id: str,
        reminder_due_at: datetime,
        claim_id: str,
        sent_at: datetime,
    ) -> bool:
        self._validate_id(todo_id)
        try:
            with self.manager.get_connection() as connection:
                cursor = connection.execute(
                    "UPDATE todos SET reminder_sent_at = %s, reminder_claimed_until = NULL, reminder_claim_id = NULL WHERE id = %s AND reminder_due_at = %s AND reminder_claim_id = %s AND reminder_sent_at IS NULL AND completed = FALSE",
                    (sent_at, todo_id, reminder_due_at, claim_id),
                )
            return cursor.rowcount > 0
        except psycopg.Error as error:
            raise TodoRepositoryError("Todo storage operation failed.") from error

    def release_reminder_claim(
        self, todo_id: str, reminder_due_at: datetime, claim_id: str
    ) -> bool:
        self._validate_id(todo_id)
        try:
            with self.manager.get_connection() as connection:
                cursor = connection.execute(
                    "UPDATE todos SET reminder_claimed_until = NULL, reminder_claim_id = NULL WHERE id = %s AND reminder_due_at = %s AND reminder_claim_id = %s AND reminder_sent_at IS NULL",
                    (todo_id, reminder_due_at, claim_id),
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
            due_date=row[4],
            owner_id=row[5],
            reminder_due_at=row[6],
            reminder_sent_at=row[7],
            reminder_claimed_until=row[8],
            reminder_claim_id=row[9],
        )
