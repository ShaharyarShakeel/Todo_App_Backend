"""Initializes and manages all database connections, handles database switching, and routes user operations to the correct database."""
from contextvars import ContextVar
from dataclasses import dataclass
import secrets
from threading import RLock
from typing import Dict, Optional

from domain.entities.todo import Todo
from domain.entities.user import User
from domain.repositories.todo_repository import TodoRepository
from domain.repositories.user_repository import UserRepository


SUPPORTED_PROVIDERS = ("mongodb", "firebase", "postgresql")
_request_provider: ContextVar[Optional[str]] = ContextVar(
    "todo_api_request_provider", default=None
)


@dataclass
class ProviderBundle:
    provider: str
    todo_repository: TodoRepository
    user_repository: UserRepository
    close: object


class DatabaseCatalog:
    """Keeps all database adapters available and routes each operation by provider."""

    def __init__(self, default_provider: str):
        self._lock = RLock()
        self._default_provider = self.validate_provider(default_provider)
        # A fresh process epoch also invalidates tokens issued before a restart.
        self._session_generation = secrets.randbits(63)
        self._providers: Dict[str, ProviderBundle] = {}

    @staticmethod
    def validate_provider(provider: str) -> str:
        if not isinstance(provider, str) or provider.strip().lower() not in SUPPORTED_PROVIDERS:
            raise ValueError(
                "Provider must be one of: mongodb, firebase, postgresql."
            )
        return provider.strip().lower()

    @property
    def default_provider(self) -> str:
        with self._lock:
            return self._default_provider

    @property
    def session_generation(self) -> int:
        with self._lock:
            return self._session_generation

    def registration_context(self) -> tuple[str, int]:
        """Return a consistent provider/generation snapshot for auth operations."""
        with self._lock:
            return self._default_provider, self._session_generation

    def initialize_all(self) -> None:
        if self._providers:
            return
        initialized = {}
        try:
            initialized["mongodb"] = self._initialize_mongodb()
            initialized["firebase"] = self._initialize_firebase()
            initialized["postgresql"] = self._initialize_postgresql()
            self._providers = initialized
        except Exception:
            # Close only providers that completed initialization. Importing every
            # provider's close function here can re-trigger the failing import and
            # hide the original startup error (for example, missing firebase_admin).
            for bundle in reversed(list(initialized.values())):
                try:
                    bundle.close()
                except Exception:
                    pass
            raise

    def _initialize_mongodb(self) -> ProviderBundle:
        from infrastructure.database.mongodb.client import (
            close_mongodb_connection,
            connect_to_mongodb,
            get_todo_collection,
            get_user_collection,
        )
        from infrastructure.repositories.mongodb.todo_repository import MongoTodoRepository
        from infrastructure.repositories.mongodb.user_repository import MongoUserRepository

        connect_to_mongodb()
        todos = MongoTodoRepository(get_todo_collection())
        users = MongoUserRepository(get_user_collection())
        users.ensure_indexes()
        return ProviderBundle("mongodb", todos, users, close_mongodb_connection)

    def _initialize_firebase(self) -> ProviderBundle:
        from infrastructure.database.firebase.client import (
            close_firebase,
            connect_to_firebase,
        )
        from infrastructure.repositories.firebase.todo_repository import FirebaseTodoRepository
        from infrastructure.repositories.firebase.user_repository import FirebaseUserRepository

        connect_to_firebase()
        todos = FirebaseTodoRepository()
        users = FirebaseUserRepository()
        users.ensure_indexes()
        return ProviderBundle("firebase", todos, users, close_firebase)

    def _initialize_postgresql(self) -> ProviderBundle:
        from infrastructure.database.postgres.client import (
            close_postgres,
            connect_to_postgres,
        )
        from infrastructure.repositories.postgres.todo_repository import PostgresTodoRepository
        from infrastructure.repositories.postgres.user_repository import PostgresUserRepository

        connect_to_postgres()
        todos = PostgresTodoRepository()
        users = PostgresUserRepository()
        users.ensure_indexes()
        return ProviderBundle("postgresql", todos, users, close_postgres)

    def close_all(self) -> None:
        with self._lock:
            bundles = list(self._providers.values())
            self._providers.clear()
        errors = []
        for bundle in reversed(bundles):
            try:
                bundle.close()
            except Exception as error:
                errors.append(error)
        if errors:
            raise RuntimeError("One or more database providers failed to close.") from errors[0]

    def switch_default(self, provider: str) -> tuple[str, str, bool]:
        provider = self.validate_provider(provider)
        with self._lock:
            if provider not in self._providers:
                raise RuntimeError(f"Database provider '{provider}' is not initialized.")
            previous = self._default_provider
            if provider == previous:
                return previous, provider, False
            self._default_provider = provider
            self._session_generation += 1
            return previous, provider, True

    def user_repository_for(self, provider: str) -> UserRepository:
        provider = self.validate_provider(provider)
        try:
            return self._providers[provider].user_repository
        except KeyError as error:
            raise RuntimeError(f"Database provider '{provider}' is not initialized.") from error

    def todo_repository_for(self, provider: str) -> TodoRepository:
        provider = self.validate_provider(provider)
        try:
            return self._providers[provider].todo_repository
        except KeyError as error:
            raise RuntimeError(f"Database provider '{provider}' is not initialized.") from error

    def new_user_id(self, provider: str, email: str) -> str:
        repository = self.user_repository_for(provider)
        return repository.new_user_id(email)

    def set_request_provider(self, provider: str) -> None:
        _request_provider.set(self.validate_provider(provider))

    def request_provider(self) -> str:
        provider = _request_provider.get()
        if provider is None:
            raise RuntimeError(
                "No authenticated request database provider is set; "
                "Todo operations require a validated account assignment."
            )
        return provider

    def request_scope(self):
        return _request_provider


class DynamicTodoRepository(TodoRepository):
    """Stable use-case dependency that selects the request's assigned provider."""

    def __init__(self, catalog: DatabaseCatalog):
        self.catalog = catalog

    def create(self, todo: Todo) -> Todo:
        return self._repository().create(todo)

    def get_all(self, owner_id: str):
        return self._repository().get_all(owner_id)

    def get_by_id(self, todo_id: str, owner_id: str):
        return self._repository().get_by_id(todo_id, owner_id)

    def update(self, todo: Todo):
        return self._repository().update(todo)

    def delete(self, todo_id: str, owner_id: str) -> bool:
        return self._repository().delete(todo_id, owner_id)

    def _repository(self) -> TodoRepository:
        return self.catalog.todo_repository_for(self.catalog.request_provider())


class DynamicUserRepository(UserRepository):
    """Stable user-repository dependency for legacy/non-registry use cases."""

    def __init__(self, catalog: DatabaseCatalog):
        self.catalog = catalog

    def create(self, user: User) -> User:
        return self._repository().create(user)

    def get_by_email(self, email: str):
        return self._repository().get_by_email(email)

    def get_by_id(self, user_id: str):
        return self._repository().get_by_id(user_id)

    def list_users(self):
        return self._repository().list_users()

    def new_user_id(self, email: str) -> str:
        return self._repository().new_user_id(email)

    def ensure_indexes(self) -> None:
        for provider in SUPPORTED_PROVIDERS:
            self.catalog.user_repository_for(provider).ensure_indexes()

    def _repository(self) -> UserRepository:
        return self.catalog.user_repository_for(self.catalog.request_provider())


class ProviderRequestScopeMiddleware:
    """Clears per-request provider state so it cannot leak between requests."""

    def __init__(self, app, catalog: DatabaseCatalog):
        self.app = app
        self.catalog = catalog

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        context = self.catalog.request_scope()
        token = context.set(None)
        try:
            await self.app(scope, receive, send)
        finally:
            context.reset(token)
