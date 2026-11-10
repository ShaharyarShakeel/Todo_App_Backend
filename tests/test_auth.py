import unittest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from domain.entities.user import User
from domain.repositories.user_repository import UserRepository
from infrastructure.security.auth import PasswordHasher, TokenService
from application.use_cases.sign_up import SignUp
from application.use_cases.log_in import LogIn
from presentation.controllers.auth_controller import AuthController
from presentation.routes.auth_routes import create_auth_routes


class InMemoryUserRepository(UserRepository):
    def __init__(self):
        self.users = {}
        self.next_id = 1

    def create(self, user: User) -> User:
        user.id = str(self.next_id)
        self.next_id += 1
        self.users[user.email] = user
        return user

    def get_by_email(self, email: str):
        return self.users.get(email.strip().lower())

    def get_by_id(self, user_id: str):
        return next((user for user in self.users.values() if user.id == user_id), None)

    def list_users(self):
        return list(self.users.values())

    def new_user_id(self, email: str) -> str:
        return str(self.next_id)


class TestAuthenticationEndpoints(unittest.TestCase):
    def setUp(self):
        self.repository = InMemoryUserRepository()
        self.password_hasher = PasswordHasher()
        self.token_service = TokenService()
        controller = AuthController(
            sign_up=SignUp(self.repository, self.password_hasher, self.token_service),
            log_in=LogIn(self.repository, self.password_hasher, self.token_service),
        )
        app = FastAPI()
        app.include_router(create_auth_routes(controller))
        self.client = TestClient(app)

    def test_signup_and_login(self):
        signup_response = self.client.post(
            "/auth/signup",
            json={"email": "Person@example.com", "password": "correct-horse"},
        )

        self.assertEqual(signup_response.status_code, 201)
        signup_data = signup_response.json()
        self.assertEqual(signup_data["email"], "person@example.com")
        self.assertEqual(signup_data["token_type"], "bearer")
        self.assertEqual(
            self.token_service.get_subject(signup_data["access_token"]),
            signup_data["id"],
        )
        self.assertNotEqual(
            self.repository.get_by_email("person@example.com").password_hash,
            "correct-horse",
        )

        login_response = self.client.post(
            "/auth/login",
            json={"email": "PERSON@example.com", "password": "correct-horse"},
        )

        self.assertEqual(login_response.status_code, 200)
        self.assertEqual(
            self.token_service.get_subject(login_response.json()["access_token"]),
            login_response.json()["id"],
        )

    def test_duplicate_signup_is_rejected(self):
        payload = {"email": "person@example.com", "password": "correct-horse"}
        self.client.post("/auth/signup", json=payload)

        response = self.client.post("/auth/signup", json=payload)

        self.assertEqual(response.status_code, 409)

    def test_invalid_login_is_rejected(self):
        response = self.client.post(
            "/auth/login",
            json={"email": "person@example.com", "password": "incorrect-pass"},
        )

        self.assertEqual(response.status_code, 401)

    def test_signup_validation(self):
        response = self.client.post(
            "/auth/signup",
            json={"email": "not-an-email", "password": "short"},
        )

        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
