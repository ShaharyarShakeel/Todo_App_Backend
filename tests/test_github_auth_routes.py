import unittest

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from application.dtos.auth_dto import AuthDTO
from presentation.routes.auth_routes import create_auth_routes


class StubAuthController:
    def __init__(self):
        self.received_codes = []
        self.fail_authentication = False

    def github_authorization_url(self, state):
        return f"https://github.com/login/oauth/authorize?state={state}"

    def authenticate_with_github(self, code):
        self.received_codes.append(code)
        if self.fail_authentication:
            raise HTTPException(status_code=401, detail="GitHub account has no verified email.")
        return AuthDTO(id="global-user-id", email="person@example.com", access_token="app-jwt")


class TestGitHubAuthRoutes(unittest.TestCase):
    def setUp(self):
        self.controller = StubAuthController()
        app = FastAPI()
        app.state.github_redirect_uri = "http://localhost:8000/auth/github/callback"
        app.state.frontend_url = "http://localhost:5173"
        app.include_router(create_auth_routes(self.controller))
        self.client = TestClient(app, follow_redirects=False)

    def test_github_oauth_callback_checks_state_and_redirects_result_in_fragment(self):
        start = self.client.get("/auth/github")
        self.assertEqual(start.status_code, 302)
        state_cookie = start.cookies["github_oauth_state"]
        self.assertIn(f"state={state_cookie}", start.headers["location"])

        callback = self.client.get(
            "/auth/github/callback",
            params={"code": "temporary-code", "state": state_cookie},
        )

        self.assertEqual(callback.status_code, 303)
        self.assertTrue(callback.headers["location"].startswith("http://localhost:5173/#"))
        self.assertIn("github_access_token=app-jwt", callback.headers["location"])
        self.assertEqual(self.controller.received_codes, ["temporary-code"])
        self.assertIn("github_oauth_state", callback.headers["set-cookie"])

    def test_github_oauth_callback_rejects_state_mismatch(self):
        self.client.get("/auth/github")
        callback = self.client.get(
            "/auth/github/callback", params={"code": "temporary-code", "state": "wrong"}
        )

        self.assertEqual(callback.status_code, 303)
        self.assertIn("github_error=invalid_state", callback.headers["location"])
        self.assertEqual(self.controller.received_codes, [])

    def test_github_callback_redirect_preserves_sanitized_failure_reason(self):
        self.controller.fail_authentication = True
        start = self.client.get("/auth/github")
        state_cookie = start.cookies["github_oauth_state"]

        callback = self.client.get(
            "/auth/github/callback",
            params={"code": "temporary-code", "state": state_cookie},
        )

        self.assertEqual(callback.status_code, 303)
        self.assertIn("github_message=GitHub+account+has+no+verified+email.", callback.headers["location"])


if __name__ == "__main__":
    unittest.main()
