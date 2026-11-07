import unittest
from unittest.mock import Mock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pymongo.errors import PyMongoError
from bson import ObjectId

from infrastructure.repositories.in_memory_todo_repository import (
    InMemoryTodoRepository,
)
from infrastructure.repositories.mongodb.todo_repository import MongoTodoRepository
from application.use_cases.create_todo import CreateTodo
from application.use_cases.get_todo import GetTodo
from application.use_cases.get_all_todos import GetAllTodos
from application.use_cases.update_todo import UpdateTodo
from application.use_cases.patch_todo import PatchTodo
from application.use_cases.delete_todo import DeleteTodo
from application.exceptions import TodoRepositoryError
from domain.exceptions.todo_exceptions import InvalidTodoIdError
from domain.entities.todo import Todo
from domain.entities.user import User
from presentation.controllers.todo_controller import TodoController
from presentation.routes.todo_routes import create_todo_routes
from infrastructure.security.auth import TokenService


class TestTodoAPIEndpoints(unittest.TestCase):
    """End-to-End API tests for the Presentation Layer with decoupled InMemory repository."""

    def setUp(self):
        self.repository = InMemoryTodoRepository()
        controller = TodoController(
            create_todo=CreateTodo(self.repository),
            get_todo=GetTodo(self.repository),
            get_all_todos=GetAllTodos(self.repository),
            update_todo=UpdateTodo(self.repository),
            patch_todo=PatchTodo(self.repository),
            delete_todo=DeleteTodo(self.repository),
        )

        test_app = FastAPI()
        test_app.state.user_repository = Mock()
        test_app.state.user_repository.get_by_id.return_value = User(
            user_id="test@example.com",
            email="test@example.com",
            password_hash="test-hash",
        )
        test_app.include_router(create_todo_routes(controller))
        self.test_app = test_app
        self.unauthenticated_client = TestClient(test_app)
        self.client = TestClient(test_app)
        token = TokenService().create_access_token("test@example.com")
        self.client.headers["Authorization"] = f"Bearer {token}"

    def test_crud_lifecycle(self):
        # 1. Create
        create_resp = self.client.post(
            "/todos/",
            json={"title": "Integration Todo", "description": "Testing CRUD"},
        )
        self.assertEqual(create_resp.status_code, 201)
        data = create_resp.json()
        self.assertEqual(data["title"], "Integration Todo")
        self.assertFalse(data["completed"])
        todo_id = data["id"]

        # 2. Get All
        list_resp = self.client.get("/todos/")
        self.assertEqual(list_resp.status_code, 200)
        self.assertEqual(len(list_resp.json()), 1)

        # 3. Get by ID
        get_resp = self.client.get(f"/todos/{todo_id}")
        self.assertEqual(get_resp.status_code, 200)
        self.assertEqual(get_resp.json()["id"], todo_id)

        # 4. Update (PUT)
        put_resp = self.client.put(
            f"/todos/{todo_id}",
            json={
                "title": "Updated Integration Todo",
                "description": "Updated desc",
                "completed": True,
            },
        )
        self.assertEqual(put_resp.status_code, 200)
        self.assertEqual(put_resp.json()["title"], "Updated Integration Todo")
        self.assertTrue(put_resp.json()["completed"])

        # 5. Patch (PATCH)
        patch_resp = self.client.patch(
            f"/todos/{todo_id}",
            json={"completed": False},
        )
        self.assertEqual(patch_resp.status_code, 200)
        self.assertFalse(patch_resp.json()["completed"])

        # 6. Delete
        delete_resp = self.client.delete(f"/todos/{todo_id}")
        self.assertEqual(delete_resp.status_code, 200)

        # 7. Verify Not Found after deletion
        not_found_resp = self.client.get(f"/todos/{todo_id}")
        self.assertEqual(not_found_resp.status_code, 404)

    def test_todos_are_isolated_between_users_for_all_operations(self):
        first_todo = self.client.post(
            "/todos/",
            json={"title": "First user's todo"},
        ).json()

        other_client = TestClient(self.test_app)
        other_token = TokenService().create_access_token("second-user")
        other_client.headers["Authorization"] = f"Bearer {other_token}"
        self.assertEqual(other_client.get("/todos/").json(), [])

        second_todo = other_client.post(
            "/todos/",
            json={"title": "Second user's todo"},
        ).json()

        self.assertEqual(len(self.client.get("/todos/").json()), 1)
        self.assertEqual(len(other_client.get("/todos/").json()), 1)
        self.assertEqual(other_client.get(f"/todos/{first_todo['id']}").status_code, 404)
        self.assertEqual(
            other_client.put(
                f"/todos/{first_todo['id']}",
                json={"title": "Hijacked", "completed": True},
            ).status_code,
            404,
        )
        self.assertEqual(
            other_client.patch(
                f"/todos/{first_todo['id']}",
                json={"title": "Hijacked"},
            ).status_code,
            404,
        )
        self.assertEqual(
            other_client.delete(f"/todos/{first_todo['id']}").status_code,
            404,
        )
        self.assertEqual(self.client.get(f"/todos/{second_todo['id']}").status_code, 404)
        self.assertEqual(
            self.client.get(f"/todos/{first_todo['id']}").json()["title"],
            "First user's todo",
        )

    def test_todo_routes_require_a_valid_access_token(self):
        response = self.unauthenticated_client.get("/todos/")
        self.assertEqual(response.status_code, 401)

        invalid_token_response = self.unauthenticated_client.get(
            "/todos/",
            headers={"Authorization": "Bearer invalid-token"},
        )
        self.assertEqual(invalid_token_response.status_code, 401)

    def test_todo_routes_reject_token_when_user_no_longer_exists(self):
        self.test_app.state.user_repository.get_by_id.return_value = None

        response = self.client.post("/todos/", json={"title": "Should not be created"})

        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.repository.get_all("test@example.com"), [])

    def test_validation_errors(self):
        resp = self.client.post("/todos/", json={"title": ""})
        self.assertEqual(resp.status_code, 422)

    def test_invalid_todo_id_returns_400(self):
        self.repository.get_by_id = Mock(
            side_effect=InvalidTodoIdError("Todo ID is invalid.")
        )

        response = self.client.get("/todos/invalid-id")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Todo ID is invalid.")

    def test_storage_error_returns_503(self):
        self.repository.get_all = Mock(
            side_effect=TodoRepositoryError("Database details should not leak.")
        )

        response = self.client.get("/todos/")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json()["detail"],
            "Todo storage is temporarily unavailable.",
        )

    def test_mongo_errors_are_wrapped_as_repository_errors(self):
        collection = Mock()
        collection.find.side_effect = PyMongoError("database details")
        repository = MongoTodoRepository(collection=collection)

        with self.assertRaises(TodoRepositoryError):
            repository.get_all("user-1")

    def test_mongo_repository_scopes_each_operation_to_the_owner(self):
        collection = Mock()
        collection.find.return_value = []
        collection.find_one.return_value = None
        collection.update_one.return_value.matched_count = 0
        collection.delete_one.return_value.deleted_count = 0
        repository = MongoTodoRepository(collection=collection)
        todo_id = str(ObjectId())
        owner_id = "owner-123"

        repository.get_all(owner_id)
        collection.find.assert_called_once_with({"owner_id": owner_id})

        repository.get_by_id(todo_id, owner_id)
        collection.find_one.assert_called_once_with(
            {"_id": ObjectId(todo_id), "owner_id": owner_id}
        )

        repository.update(
            Todo(todo_id=todo_id, title="Owned", owner_id=owner_id)
        )
        self.assertEqual(
            collection.update_one.call_args.args[0],
            {"_id": ObjectId(todo_id), "owner_id": owner_id},
        )

        repository.delete(todo_id, owner_id)
        collection.delete_one.assert_called_once_with(
            {"_id": ObjectId(todo_id), "owner_id": owner_id}
        )

    def test_mongo_repository_rejects_invalid_object_id(self):
        collection = Mock()
        repository = MongoTodoRepository(collection=collection)

        with self.assertRaises(InvalidTodoIdError):
            repository.get_by_id("invalid-id", "user-1")

        collection.find_one.assert_not_called()


if __name__ == "__main__":
    unittest.main()
