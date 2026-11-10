import hashlib
import os
import subprocess
import sys
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event, Lock
from uuid import uuid4
from unittest.mock import patch

from bson import ObjectId
from fastapi import FastAPI
from fastapi.testclient import TestClient

from application.exceptions import (
    AccountRegistryConflictError,
    UserAlreadyExistsError,
    UserRepositoryError,
)
from application.use_cases.create_todo import CreateTodo
from application.use_cases.delete_todo import DeleteTodo
from application.use_cases.get_all_todos import GetAllTodos
from application.use_cases.get_todo import GetTodo
from application.use_cases.log_in import LogIn
from application.use_cases.patch_todo import PatchTodo
from application.use_cases.sign_up import SignUp
from application.use_cases.update_todo import UpdateTodo
from domain.entities.account_assignment import AccountAssignment
from domain.entities.user import User
from infrastructure.database.account_registry_initializer import AccountRegistryInitializer
from infrastructure.database.provider_catalog import (
    DatabaseCatalog,
    DynamicTodoRepository,
    DynamicUserRepository,
    ProviderBundle,
    ProviderRequestScopeMiddleware,
)
from infrastructure.database.switch_pipe import DatabaseSwitchPipeServer
from infrastructure.repositories.in_memory_todo_repository import InMemoryTodoRepository
from infrastructure.repositories.mongodb.account_registry_repository import (
    MongoAccountRegistryRepository,
)
from infrastructure.security.auth import TokenService
from presentation.controllers.auth_controller import AuthController
from presentation.controllers.todo_controller import TodoController
from presentation.routes.auth_routes import create_auth_routes
from presentation.routes.todo_routes import create_todo_routes


class MemoryUserRepository:
    def __init__(self, provider):
        self.provider = provider
        self.users = {}
        self.lock = Lock()

    def ensure_indexes(self):
        pass

    def new_user_id(self, email):
        if self.provider == "mongodb":
            return str(ObjectId())
        if self.provider == "firebase":
            return hashlib.sha256(email.strip().lower().encode()).hexdigest()
        return str(uuid4())

    def create(self, user):
        with self.lock:
            if user.id in self.users or any(x.email == user.email for x in self.users.values()):
                raise UserAlreadyExistsError("duplicate")
            self.users[user.id] = user
        return user

    def get_by_email(self, email):
        return next((x for x in self.users.values() if x.email == email.strip().lower()), None)

    def get_by_id(self, user_id):
        return self.users.get(user_id)

    def list_users(self):
        return list(self.users.values())


class MemoryRegistry:
    def __init__(self):
        self.by_id = {}
        self.by_email = {}
        self.lock = Lock()

    def ensure_indexes(self):
        pass

    def reserve(self, assignment):
        with self.lock:
            email_provider = (assignment.email_normalized, assignment.provider)
            if assignment.user_id in self.by_id or email_provider in self.by_email:
                raise UserAlreadyExistsError("duplicate")
            pending = AccountAssignment(
                assignment.user_id,
                assignment.email_normalized,
                assignment.provider,
                assignment.provider_user_id,
                "pending",
            )
            self.by_id[pending.user_id] = pending
            self.by_email[email_provider] = pending

    def activate(self, user_id):
        with self.lock:
            record = self.by_id[user_id]
            active = AccountAssignment(
                record.user_id,
                record.email_normalized,
                record.provider,
                record.provider_user_id,
                "active",
            )
            self.by_id[user_id] = active
            self.by_email[(active.email_normalized, active.provider)] = active

    def delete_pending(self, user_id):
        with self.lock:
            record = self.by_id.get(user_id)
            if record and record.status == "pending":
                self.by_id.pop(user_id)
                self.by_email.pop((record.email_normalized, record.provider), None)

    def add_existing(self, assignment):
        self.reserve(assignment)
        self.activate(assignment.user_id)

    def get_by_email(self, email_normalized, provider):
        return self.by_email.get((email_normalized, provider))

    def get_by_user_id(self, user_id):
        return self.by_id.get(user_id)

    def get_by_provider_user_id(self, provider_user_id):
        return [
            x for x in self.by_id.values()
            if x.provider_user_id == provider_user_id and x.status == "active"
        ]

    def list_all(self):
        return [x for x in self.by_id.values() if x.status == "active"]

    def list_pending(self):
        return [x for x in self.by_id.values() if x.status == "pending"]


class FastHasher:
    def hash(self, password):
        return "hash:" + password

    def verify(self, password, hashed):
        return hashed == "hash:" + password


class TestMultiDatabaseRouting(unittest.TestCase):
    def setUp(self):
        self.catalog = DatabaseCatalog("mongodb")
        for provider in ("mongodb", "firebase", "postgresql"):
            self.catalog._providers[provider] = ProviderBundle(
                provider,
                InMemoryTodoRepository(),
                MemoryUserRepository(provider),
                lambda: None,
            )
        self.registry = MemoryRegistry()
        self.token_service = TokenService()
        self.sign_up = SignUp(
            DynamicUserRepository(self.catalog),
            FastHasher(),
            self.token_service,
            account_registry=self.registry,
            provider_catalog=self.catalog,
        )
        self.log_in = LogIn(
            DynamicUserRepository(self.catalog),
            FastHasher(),
            self.token_service,
            account_registry=self.registry,
            provider_catalog=self.catalog,
        )
        todo_controller = TodoController(
            create_todo=CreateTodo(DynamicTodoRepository(self.catalog)),
            get_todo=GetTodo(DynamicTodoRepository(self.catalog)),
            get_all_todos=GetAllTodos(DynamicTodoRepository(self.catalog)),
            update_todo=UpdateTodo(DynamicTodoRepository(self.catalog)),
            patch_todo=PatchTodo(DynamicTodoRepository(self.catalog)),
            delete_todo=DeleteTodo(DynamicTodoRepository(self.catalog)),
        )
        app = FastAPI()
        app.state.provider_catalog = self.catalog
        app.state.account_registry = self.registry
        app.state.token_service = self.token_service
        app.add_middleware(ProviderRequestScopeMiddleware, catalog=self.catalog)
        app.include_router(create_auth_routes(AuthController(self.sign_up, self.log_in)))
        app.include_router(create_todo_routes(todo_controller))
        self.app = app
        self.client = TestClient(app)

    def signup(self, provider, email):
        self.catalog.switch_default(provider)
        response = self.client.post(
            "/auth/signup", json={"email": email, "password": "pass-12345"}
        )
        self.assertEqual(response.status_code, 201, response.text)
        data = response.json()
        assignment = self.registry.get_by_email(email.strip().lower(), provider)
        self.assertEqual(assignment.provider, provider)
        claims = self.token_service.get_claims(data["access_token"])
        self.assertEqual(claims["sub"], assignment.user_id)
        self.assertEqual(claims["provider"], provider)
        return data

    def test_users_stay_assigned_and_todo_crud_uses_the_authenticated_provider(self):
        users = [
            ("mongodb", "a@example.com"),
            ("firebase", "b@example.com"),
            ("postgresql", "c@example.com"),
            ("mongodb", "d@example.com"),
        ]
        for provider, email in users:
            self.catalog.switch_default(provider)
            signup_response = self.client.post(
                "/auth/signup", json={"email": email, "password": "pass-12345"}
            )
            self.assertEqual(signup_response.status_code, 201, signup_response.text)
            assignment = self.registry.get_by_email(email, provider)
            login = self.client.post(
                "/auth/login", json={"email": email, "password": "pass-12345"}
            )
            self.assertEqual(login.status_code, 200, login.text)
            login_claims = self.token_service.get_claims(login.json()["access_token"])
            self.assertEqual(login_claims["provider"], provider)
            headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
            response = self.client.post(
                "/todos/",
                json={"title": email},
                headers=headers,
            )
            self.assertEqual(response.status_code, 201, response.text)
            todo_id = response.json()["id"]
            repository = self.catalog.todo_repository_for(provider)
            self.assertEqual(len(repository.get_all(assignment.provider_user_id)), 1)

            self.assertEqual(self.client.get("/todos/", headers=headers).status_code, 200)
            self.assertEqual(
                self.client.get(f"/todos/{todo_id}", headers=headers).status_code, 200
            )
            self.assertEqual(
                self.client.put(
                    f"/todos/{todo_id}",
                    json={"title": "Updated", "completed": True},
                    headers=headers,
                ).status_code,
                200,
            )
            self.assertEqual(
                self.client.patch(
                    f"/todos/{todo_id}",
                    json={"completed": False},
                    headers=headers,
                ).status_code,
                200,
            )
            self.assertEqual(
                self.client.delete(f"/todos/{todo_id}", headers=headers).status_code,
                200,
            )

    def test_same_email_is_allowed_across_providers_but_not_twice_in_one(self):
        self.signup("mongodb", "same@example.com")
        self.catalog.switch_default("firebase")
        firebase_signup = self.client.post(
            "/auth/signup", json={"email": "SAME@example.com", "password": "pass-12345"}
        )
        self.assertEqual(firebase_signup.status_code, 201, firebase_signup.text)
        self.assertIsNotNone(self.registry.get_by_email("same@example.com", "mongodb"))
        self.assertIsNotNone(self.registry.get_by_email("same@example.com", "firebase"))
        response = self.client.post(
            "/auth/signup", json={"email": "SAME@example.com", "password": "pass-12345"}
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(len(self.catalog.user_repository_for("firebase").list_users()), 1)

    def test_login_searches_only_the_selected_default_provider(self):
        self.signup("mongodb", "provider-login@example.com")
        self.catalog.switch_default("firebase")
        response = self.client.post(
            "/auth/login",
            json={"email": "provider-login@example.com", "password": "pass-12345"},
        )
        self.assertEqual(response.status_code, 401)

    def test_default_switch_invalidates_old_tokens_even_after_switching_back(self):
        account = self.signup("mongodb", "generation@example.com")
        old_token = account["access_token"]
        self.catalog.switch_default("firebase")
        generation_after_switch = self.catalog.session_generation
        self.catalog.switch_default("firebase")
        self.assertEqual(self.catalog.session_generation, generation_after_switch)

        headers = {"Authorization": f"Bearer {old_token}"}
        self.assertEqual(
            self.client.post("/todos/", json={"title": "blocked"}, headers=headers).status_code,
            401,
        )
        self.catalog.switch_default("mongodb")
        self.assertEqual(
            self.client.post("/todos/", json={"title": "still blocked"}, headers=headers).status_code,
            401,
        )

        login = self.client.post(
            "/auth/login",
            json={"email": "generation@example.com", "password": "pass-12345"},
        )
        self.assertEqual(login.status_code, 200, login.text)
        claims = self.token_service.get_claims(login.json()["access_token"])
        self.assertEqual(claims["provider"], "mongodb")
        self.assertEqual(claims["session_generation"], self.catalog.session_generation)
        self.assertEqual(
            self.client.post(
                "/todos/",
                json={"title": "allowed after login"},
                headers={"Authorization": f"Bearer {login.json()['access_token']}"},
            ).status_code,
            201,
        )

    def test_same_email_accounts_login_from_the_selected_provider(self):
        for provider in ("mongodb", "firebase", "postgresql"):
            self.catalog.switch_default(provider)
            response = self.client.post(
                "/auth/signup",
                json={"email": "shared@example.com", "password": "pass-12345"},
            )
            self.assertEqual(response.status_code, 201, response.text)

        for provider in ("mongodb", "firebase", "postgresql"):
            self.catalog.switch_default(provider)
            response = self.client.post(
                "/auth/login",
                json={"email": "shared@example.com", "password": "pass-12345"},
            )
            self.assertEqual(response.status_code, 200, response.text)
            claims = self.token_service.get_claims(response.json()["access_token"])
            self.assertEqual(claims["provider"], provider)

    def test_deleted_user_and_invalid_provider_claim_are_rejected(self):
        account = self.signup("postgresql", "deleted@example.com")
        assignment = self.registry.get_by_email("deleted@example.com", "postgresql")
        self.catalog.user_repository_for("postgresql").users.pop(assignment.provider_user_id)

        deleted_response = self.client.post(
            "/todos/",
            json={"title": "blocked"},
            headers={"Authorization": f"Bearer {account['access_token']}"},
        )
        self.assertEqual(deleted_response.status_code, 401)

        invalid_token = self.token_service.create_access_token(assignment.user_id, provider="other")
        invalid_response = self.client.post(
            "/todos/",
            json={"title": "blocked"},
            headers={"Authorization": f"Bearer {invalid_token}"},
        )
        self.assertEqual(invalid_response.status_code, 401)

    def test_concurrent_signup_reserves_email_once(self):
        def register():
            try:
                return self.sign_up.execute("race@example.com", "pw")
            except UserAlreadyExistsError:
                return None

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(lambda _: register(), range(2)))
        self.assertEqual(sum(result is not None for result in outcomes), 1)
        self.assertEqual(len(self.registry.list_all()), 1)
        self.assertEqual(len(self.catalog.user_repository_for("mongodb").list_users()), 1)

    def test_database_error_does_not_fall_back_to_another_provider(self):
        account = self.signup("mongodb", "offline@example.com")
        assignment = self.registry.get_by_email("offline@example.com", "mongodb")

        def unavailable(_user_id):
            raise UserRepositoryError("offline")

        self.catalog.user_repository_for("mongodb").get_by_id = unavailable
        response = self.client.post(
            "/todos/",
            json={"title": "blocked"},
            headers={"Authorization": f"Bearer {account['access_token']}"},
        )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(assignment.provider, "mongodb")

    def test_default_switch_during_inflight_request_does_not_change_request_provider(self):
        account = self.signup("mongodb", "inflight@example.com")
        entered = Event()
        resume = Event()
        mongo_todos = self.catalog.todo_repository_for("mongodb")
        original_create = mongo_todos.create

        def slow_create(todo):
            entered.set()
            if not resume.wait(3):
                raise TimeoutError("test request did not resume")
            return original_create(todo)

        mongo_todos.create = slow_create
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(
                self.client.post,
                "/todos/",
                json={"title": "in flight"},
                headers={"Authorization": f"Bearer {account['access_token']}"},
            )
            self.assertTrue(entered.wait(2))
            self.catalog.switch_default("firebase")
            resume.set()
            response = pending.result(timeout=4)

        self.assertEqual(response.status_code, 201, response.text)
        owner_id = self.registry.get_by_email("inflight@example.com", "mongodb").provider_user_id
        self.assertEqual(len(mongo_todos.get_all(owner_id)), 1)
        self.assertEqual(len(self.catalog.todo_repository_for("firebase").get_all(owner_id)), 0)

    def test_simultaneous_requests_route_to_each_users_assigned_database(self):
        accounts = {
            provider: self.signup(provider, f"{provider}@parallel.example")
            for provider in ("mongodb", "firebase", "postgresql")
        }
        # Model three valid tokens issued in the same active generation so the
        # requests can overlap while exercising ContextVar isolation.
        for provider in accounts:
            assignment = self.registry.get_by_email(
                f"{provider}@parallel.example", provider
            )
            accounts[provider] = {
                "access_token": self.token_service.create_access_token(
                    assignment.user_id,
                    provider=provider,
                    session_generation=self.catalog.session_generation,
                )
            }
        barrier = __import__("threading").Barrier(3)
        originals = {}
        for provider in accounts:
            repository = self.catalog.todo_repository_for(provider)
            originals[provider] = repository.create

            def synchronized_create(todo, original=originals[provider]):
                barrier.wait(timeout=3)
                return original(todo)

            repository.create = synchronized_create

        def create(provider):
            return self.client.post(
                "/todos/",
                json={"title": provider},
                headers={"Authorization": f"Bearer {accounts[provider]['access_token']}"},
            )

        with ThreadPoolExecutor(max_workers=3) as pool:
            responses = list(pool.map(create, accounts))

        self.assertTrue(all(response.status_code == 201 for response in responses))
        for provider in accounts:
            assignment = self.registry.get_by_email(f"{provider}@parallel.example", provider)
            self.assertEqual(
                [todo.title for todo in self.catalog.todo_repository_for(provider).get_all(
                    assignment.provider_user_id
                )],
                [provider],
            )
        # Each middleware invocation resets its ContextVar after response completion.
        with self.assertRaisesRegex(RuntimeError, "No authenticated request database provider"):
            DynamicTodoRepository(self.catalog).get_all("owner")

    def test_concurrent_default_switches_are_serialized_and_keep_providers_open(self):
        close_counts = {provider: 0 for provider in ("mongodb", "firebase", "postgresql")}
        for provider in close_counts:
            self.catalog._providers[provider].close = (
                lambda name=provider: close_counts.__setitem__(name, close_counts[name] + 1)
            )
        requested = ["firebase", "postgresql", "mongodb", "firebase"] * 10
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(self.catalog.switch_default, requested))
        self.assertIn(self.catalog.default_provider, close_counts)
        self.assertEqual(close_counts, {provider: 0 for provider in close_counts})


class TestAccountRegistryBackfill(unittest.TestCase):
    def make_catalog(self):
        catalog = DatabaseCatalog("mongodb")
        for provider in ("mongodb", "firebase", "postgresql"):
            catalog._providers[provider] = ProviderBundle(
                provider, InMemoryTodoRepository(), MemoryUserRepository(provider), lambda: None
            )
        return catalog

    def test_backfill_allows_same_email_in_different_providers(self):
        catalog = self.make_catalog()
        mongo_user = User("legacy@example.com", "hash", user_id=str(ObjectId()))
        firebase_id = hashlib.sha256(b"legacy@example.com").hexdigest()
        firebase_user = User("legacy@example.com", "hash", user_id=firebase_id)
        catalog.user_repository_for("mongodb").create(mongo_user)
        catalog.user_repository_for("firebase").create(firebase_user)
        registry = MemoryRegistry()

        AccountRegistryInitializer(registry, catalog).initialize()
        self.assertEqual(registry.get_by_email("legacy@example.com", "mongodb").provider_user_id,
                         mongo_user.id)
        self.assertEqual(registry.get_by_email("legacy@example.com", "firebase").provider_user_id,
                         firebase_user.id)

    def test_backfill_maps_existing_users_without_changing_provider_ids(self):
        catalog = self.make_catalog()
        user = User(" legacy@example.com ", "hash:pw", user_id=str(ObjectId()))
        catalog.user_repository_for("mongodb").create(user)
        registry = MemoryRegistry()

        AccountRegistryInitializer(registry, catalog).initialize()

        assignment = registry.get_by_email("legacy@example.com", "mongodb")
        self.assertIsNotNone(assignment)
        self.assertEqual(assignment.provider, "mongodb")
        self.assertEqual(assignment.provider_user_id, user.id)

        login = LogIn(
            DynamicUserRepository(catalog),
            FastHasher(),
            TokenService(),
            account_registry=registry,
            provider_catalog=catalog,
        ).execute("LEGACY@example.com", "pw")
        self.assertEqual(login.id, assignment.user_id)

    def test_active_registry_assignment_with_missing_user_stops_startup(self):
        catalog = self.make_catalog()
        registry = MemoryRegistry()
        registry.add_existing(
            AccountAssignment("global-missing", "missing@example.com", "firebase", "missing-id")
        )

        with self.assertRaisesRegex(AccountRegistryConflictError, "active registry user.*missing"):
            AccountRegistryInitializer(registry, catalog).initialize()

    def test_duplicate_global_id_reservation_is_rejected(self):
        registry = MemoryRegistry()
        first = AccountAssignment("global-1", "one@example.com", "mongodb", "mongo-1", "pending")
        second = AccountAssignment("global-1", "two@example.com", "firebase", "firebase-2", "pending")
        registry.reserve(first)
        with self.assertRaises(UserAlreadyExistsError):
            registry.reserve(second)


class TestMongoAccountRegistryIndexes(unittest.TestCase):
    def test_migrates_email_unique_index_to_email_and_provider(self):
        class RecordingCollection:
            def __init__(self):
                self.dropped = []
                self.created = []

            def list_indexes(self):
                return [
                    {"name": "_id_", "key": {"_id": 1}, "unique": True},
                    {
                        "name": "email_normalized_1",
                        "key": {"email_normalized": 1},
                        "unique": True,
                    },
                ]

            def drop_index(self, name):
                self.dropped.append(name)

            def create_index(self, keys, unique=False):
                self.created.append((keys, unique))

        collection = RecordingCollection()
        MongoAccountRegistryRepository(collection).ensure_indexes()

        self.assertEqual(collection.dropped, ["email_normalized_1"])
        self.assertIn(("user_id", True), collection.created)
        self.assertIn(
            ([("email_normalized", 1), ("provider", 1)], True), collection.created
        )


class TestDatabaseCatalog(unittest.TestCase):
    def test_todo_repository_fails_when_request_provider_is_missing(self):
        catalog = DatabaseCatalog("mongodb")
        for provider in ("mongodb", "firebase", "postgresql"):
            catalog._providers[provider] = ProviderBundle(
                provider, InMemoryTodoRepository(), MemoryUserRepository(provider), lambda: None
            )
        repository = DynamicTodoRepository(catalog)

        with self.assertRaisesRegex(RuntimeError, "No authenticated request database provider"):
            repository.get_all("owner")

    def test_failed_provider_initialization_keeps_default_and_closes_partial_provider(self):
        catalog = DatabaseCatalog("mongodb")
        close_counts = {"mongo": 0}
        partial = ProviderBundle(
            "mongodb",
            InMemoryTodoRepository(),
            MemoryUserRepository("mongodb"),
            lambda: close_counts.__setitem__("mongo", close_counts["mongo"] + 1),
        )
        catalog._initialize_mongodb = lambda: partial
        catalog._initialize_firebase = lambda: (_ for _ in ()).throw(RuntimeError("offline"))

        with self.assertRaises(RuntimeError):
            catalog.initialize_all()

        self.assertEqual(catalog.default_provider, "mongodb")
        self.assertEqual(close_counts["mongo"], 1)
        self.assertEqual(catalog._providers, {})


class TestDatabaseSwitchPipe(unittest.TestCase):
    @unittest.skipUnless(os.name == "nt", "Windows Named Pipe integration test")
    def test_cli_switches_running_process_from_another_working_directory(self):
        catalog = DatabaseCatalog("mongodb")
        for provider in ("mongodb", "firebase", "postgresql"):
            catalog._providers[provider] = ProviderBundle(
                provider, InMemoryTodoRepository(), MemoryUserRepository(provider), lambda: None
            )
        pipe_name = rf"\\.\pipe\TodoApiTest-{uuid4().hex}"
        authkey = "integration-test-auth-key-".ljust(32, "x")
        server = DatabaseSwitchPipeServer(catalog, address=pipe_name, authkey=authkey)
        server.start()
        self.addCleanup(server.stop)

        with tempfile.TemporaryDirectory() as other_directory:
            environment = os.environ.copy()
            environment["DATABASE_SWITCH_PIPE_NAME"] = pipe_name
            environment["DATABASE_SWITCH_PIPE_AUTHKEY"] = authkey
            result = subprocess.run(
                [sys.executable, str(Path(__file__).resolve().parents[1] / "switch_database.py"), "firebase"],
                cwd=other_directory,
                env=environment,
                capture_output=True,
                text=True,
                timeout=10,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(catalog.default_provider, "firebase")

    @unittest.skipUnless(os.name == "nt", "Windows Named Pipe integration test")
    def test_pipe_rejects_invalid_provider_without_changing_default(self):
        catalog = DatabaseCatalog("mongodb")
        for provider in ("mongodb", "firebase", "postgresql"):
            catalog._providers[provider] = ProviderBundle(
                provider, InMemoryTodoRepository(), MemoryUserRepository(provider), lambda: None
            )
        pipe_name = rf"\\.\pipe\TodoApiInvalid-{uuid4().hex}"
        server = DatabaseSwitchPipeServer(
            catalog, address=pipe_name, authkey="integration-test-auth-key-".ljust(32, "x")
        )
        server.start()
        self.addCleanup(server.stop)

        from switch_database import send_switch_request

        response = send_switch_request(
            "not-a-provider", pipe_name, "integration-test-auth-key-".ljust(32, "x")
        )
        self.assertFalse(response["ok"])
        self.assertEqual(catalog.default_provider, "mongodb")

    @unittest.skipUnless(os.name == "nt", "Windows Named Pipe integration test")
    def test_cli_reports_backend_not_running(self):
        from switch_database import send_switch_request

        address = rf"\\.\pipe\TodoApiMissing-{uuid4().hex}"
        with self.assertRaises(ConnectionError):
            send_switch_request(
                "firebase", address, "integration-test-auth-key-".ljust(32, "x"), timeout=1
            )

    def test_cli_timeout_is_reported(self):
        from switch_database import send_switch_request

        class SlowConnection:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

            def send(self, _request):
                pass

            def recv(self):
                time.sleep(0.2)
                return {"ok": True, "message": "late"}

        with patch("switch_database._wait_for_pipe"), patch(
            "switch_database.Client", return_value=SlowConnection()
        ):
            with self.assertRaises(TimeoutError):
                send_switch_request("firebase", "pipe", "t" * 32, timeout=0.02)


if __name__ == "__main__":
    unittest.main()
