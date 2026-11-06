import unittest
from unittest.mock import patch

from bson import ObjectId
from fastapi.testclient import TestClient
from pymongo.errors import PyMongoError

from mvc.exceptions import TodoStorageError
from mvc.main import app
from mvc.models.todo_model import TodoModel
from infrastructure.security.auth import TokenService


class TestMVCErrorHandling(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app, raise_server_exceptions=False)
        token = TokenService().create_access_token("mvc-test@example.com")
        self.client.headers["Authorization"] = f"Bearer {token}"

    def test_invalid_request_returns_422(self):
        response = self.client.post("/todos/", json={"title": ""})

        self.assertEqual(response.status_code, 422)

    def test_invalid_id_returns_400(self):
        response = self.client.get("/todos/invalid-id")

        self.assertEqual(response.status_code, 400)
        self.assertIn("invalid", response.json()["detail"])

    @patch("mvc.controllers.todo_controller.TodoModel.find_by_id", return_value=None)
    def test_missing_todo_returns_404(self, find_by_id):
        response = self.client.get(f"/todos/{ObjectId()}")

        self.assertEqual(response.status_code, 404)

    @patch(
        "mvc.models.todo_model.Database.get_collection",
        side_effect=PyMongoError("database details"),
    )
    def test_database_error_returns_503(self, get_collection):
        response = self.client.get("/todos/")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json()["detail"],
            "Todo storage is temporarily unavailable.",
        )

    @patch(
        "mvc.controllers.todo_controller.TodoModel.find_all",
        side_effect=RuntimeError("internal details"),
    )
    def test_unexpected_error_returns_generic_500(self, find_all):
        response = self.client.get("/todos/")

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.json()["detail"],
            "An unexpected error occurred.",
        )

    @patch(
        "mvc.models.todo_model.Database.get_collection",
        side_effect=PyMongoError("database details"),
    )
    def test_model_wraps_database_error(self, get_collection):
        with self.assertRaises(TodoStorageError):
            TodoModel.find_all("test-user")


if __name__ == "__main__":
    unittest.main()
