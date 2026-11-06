import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from infrastructure.security.auth import TokenService
from mvc.models.user_model import UserModel
from mvc.models.todo_model import TodoModel
from mvc.routes.auth_routes import router as mvc_auth_router
from mvc.routes.todo_routes import router as mvc_todo_router


class TestMVCAuthentication(unittest.TestCase):
    def setUp(self):
        self.users = {}
        self.todos = {}
        self.token_service = TokenService()
        self.find_user_patch = patch.object(
            UserModel, "find_by_email", side_effect=self.find_user
        )
        self.create_user_patch = patch.object(
            UserModel, "create", side_effect=self.create_user
        )
        self.find_user_patch.start()
        self.create_user_patch.start()
        self.addCleanup(self.find_user_patch.stop)
        self.addCleanup(self.create_user_patch.stop)
        todo_methods = {
            "create": self.create_todo,
            "find_all": self.find_todos,
            "find_by_id": self.find_todo,
            "update": self.update_todo,
            "patch": self.patch_todo,
            "delete": self.delete_todo,
        }
        for method_name, side_effect in todo_methods.items():
            todo_patch = patch.object(TodoModel, method_name, side_effect=side_effect)
            todo_patch.start()
            self.addCleanup(todo_patch.stop)

        app = FastAPI()
        app.include_router(mvc_auth_router)
        app.include_router(mvc_todo_router)
        self.client = TestClient(app)

    def find_user(self, email):
        return self.users.get(email.strip().lower())

    def create_user(self, email, password_hash):
        user = UserModel(
            user_id=str(len(self.users) + 1),
            email=email,
            password_hash=password_hash,
        )
        self.users[user.email] = user
        return user

    def create_todo(self, title, description, owner_id):
        todo_id = f"{len(self.todos) + 1:024x}"
        todo = TodoModel(
            todo_id=todo_id,
            title=title,
            description=description,
            owner_id=owner_id,
        )
        self.todos[todo_id] = todo
        return todo

    def find_todos(self, owner_id):
        return [todo for todo in self.todos.values() if todo.owner_id == owner_id]

    def find_todo(self, todo_id, owner_id):
        todo = self.todos.get(todo_id)
        return todo if todo and todo.owner_id == owner_id else None

    def update_todo(self, todo_id, title, description, completed, owner_id):
        todo = self.find_todo(todo_id, owner_id)
        if todo is None:
            return None
        todo.title = title
        todo.description = description
        todo.completed = completed
        return todo

    def patch_todo(self, todo_id, title, description, completed, owner_id):
        todo = self.find_todo(todo_id, owner_id)
        if todo is None:
            return None
        if title is not None:
            todo.title = title
        if description is not None:
            todo.description = description
        if completed is not None:
            todo.completed = completed
        return todo

    def delete_todo(self, todo_id, owner_id):
        todo = self.find_todo(todo_id, owner_id)
        if todo is None:
            return False
        del self.todos[todo_id]
        return True

    def client_for(self, owner_id):
        client = TestClient(self.client.app)
        token = self.token_service.create_access_token(owner_id)
        client.headers["Authorization"] = f"Bearer {token}"
        return client

    def test_signup_and_login_issue_jwt(self):
        payload = {"email": "MVC@example.com", "password": "correct-horse"}

        signup_response = self.client.post("/auth/signup", json=payload)

        self.assertEqual(signup_response.status_code, 201)
        signup_data = signup_response.json()
        self.assertEqual(signup_data["email"], "mvc@example.com")
        self.assertEqual(
            self.token_service.get_subject(signup_data["access_token"]),
            signup_data["id"],
        )
        self.assertNotEqual(
            self.users["mvc@example.com"].password_hash,
            "correct-horse",
        )

        login_response = self.client.post(
            "/auth/login",
            json={"email": "MVC@example.com", "password": "correct-horse"},
        )

        self.assertEqual(login_response.status_code, 200)
        self.assertEqual(
            self.token_service.get_subject(login_response.json()["access_token"]),
            login_response.json()["id"],
        )

    def test_duplicate_signup_and_invalid_login(self):
        payload = {"email": "mvc@example.com", "password": "correct-horse"}
        self.client.post("/auth/signup", json=payload)

        duplicate_response = self.client.post("/auth/signup", json=payload)
        login_response = self.client.post(
            "/auth/login",
            json={"email": "mvc@example.com", "password": "wrong-password"},
        )

        self.assertEqual(duplicate_response.status_code, 409)
        self.assertEqual(login_response.status_code, 401)

    def test_mvc_todos_are_isolated_between_users_for_all_operations(self):
        first_client = self.client_for("mvc-user-one")
        second_client = self.client_for("mvc-user-two")
        first_todo = first_client.post(
            "/todos/",
            json={"title": "First user's todo"},
        ).json()
        second_todo = second_client.post(
            "/todos/",
            json={"title": "Second user's todo"},
        ).json()

        self.assertEqual(len(first_client.get("/todos/").json()), 1)
        self.assertEqual(len(second_client.get("/todos/").json()), 1)
        self.assertEqual(second_client.get(f"/todos/{first_todo['id']}").status_code, 404)
        self.assertEqual(
            second_client.put(
                f"/todos/{first_todo['id']}",
                json={"title": "Hijacked", "completed": True},
            ).status_code,
            404,
        )
        self.assertEqual(
            second_client.patch(
                f"/todos/{first_todo['id']}",
                json={"title": "Hijacked"},
            ).status_code,
            404,
        )
        self.assertEqual(
            second_client.delete(f"/todos/{first_todo['id']}").status_code,
            404,
        )
        self.assertEqual(first_client.get(f"/todos/{second_todo['id']}").status_code, 404)
        self.assertEqual(
            first_client.get(f"/todos/{first_todo['id']}").json()["title"],
            "First user's todo",
        )

    def test_mvc_todo_routes_require_a_valid_jwt(self):
        response = self.client.get("/todos/")
        invalid_token_response = self.client.get(
            "/todos/",
            headers={"Authorization": "Bearer invalid-token"},
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(invalid_token_response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
