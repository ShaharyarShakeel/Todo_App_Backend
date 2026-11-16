import unittest
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlparse

from application.exceptions import (
    GitHubSignInConfigurationError,
    InvalidGitHubCredentialError,
)
from infrastructure.security.github_oauth_client import GitHubOAuthClient


def response(payload):
    result = Mock()
    result.status_code = 200
    result.json.return_value = payload
    result.raise_for_status.return_value = None
    return result


class TestGitHubOAuthClient(unittest.TestCase):
    def setUp(self):
        self.client = GitHubOAuthClient(
            "github-client-id",
            "github-client-secret",
            "http://localhost:8000/auth/github/callback",
        )

    def test_authorization_url_contains_state_scope_and_registered_callback(self):
        url = self.client.authorization_url("csrf-state")
        query = parse_qs(urlparse(url).query)

        self.assertEqual(urlparse(url).netloc, "github.com")
        self.assertEqual(query["state"], ["csrf-state"])
        self.assertEqual(query["client_id"], ["github-client-id"])
        self.assertEqual(query["redirect_uri"], [self.client.redirect_uri])
        self.assertIn("user:email", query["scope"][0])

    @patch("infrastructure.security.github_oauth_client.requests.get")
    @patch("infrastructure.security.github_oauth_client.requests.post")
    def test_exchanges_code_and_requires_verified_primary_email(self, post, get):
        post.return_value = response({"access_token": "github-access-token"})
        get.side_effect = [
            response({"id": 12345}),
            response(
                [
                    {"email": "unverified@example.com", "primary": True, "verified": False},
                    {"email": "Person@example.com", "primary": True, "verified": True},
                ]
            ),
        ]

        identity = self.client.verify_code("one-time-code")

        self.assertEqual(identity.subject, "12345")
        self.assertEqual(identity.email, "person@example.com")
        self.assertEqual(post.call_args.kwargs["data"]["client_secret"], "github-client-secret")
        self.assertEqual(post.call_args.kwargs["data"]["redirect_uri"], self.client.redirect_uri)
        self.assertEqual(get.call_count, 2)

    @patch("infrastructure.security.github_oauth_client.requests.get")
    @patch("infrastructure.security.github_oauth_client.requests.post")
    def test_rejects_identity_without_verified_primary_email(self, post, get):
        post.return_value = response({"access_token": "github-access-token"})
        get.side_effect = [
            response({"id": 12345}),
            response([{"email": "person@example.com", "primary": True, "verified": False}]),
        ]

        with self.assertRaises(InvalidGitHubCredentialError):
            self.client.verify_code("one-time-code")

    @patch("infrastructure.security.github_oauth_client.requests.post")
    def test_reports_mismatched_github_client_credentials(self, post):
        post.return_value = response(
            {"error": "incorrect_client_credentials", "error_description": "redacted"}
        )

        with self.assertRaisesRegex(
            GitHubSignInConfigurationError, "client ID and secret belong to the same OAuth App"
        ):
            self.client.verify_code("one-time-code")

    @patch("infrastructure.security.github_oauth_client.requests.post")
    def test_reports_github_redirect_uri_mismatch(self, post):
        post.return_value = response(
            {"error": "redirect_uri_mismatch", "error_description": "redacted"}
        )

        with self.assertRaisesRegex(
            GitHubSignInConfigurationError, "does not match the OAuth App callback URL"
        ):
            self.client.verify_code("one-time-code")

    @patch("infrastructure.security.github_oauth_client.requests.post")
    def test_reports_expired_or_reused_github_code(self, post):
        post.return_value = response(
            {"error": "bad_verification_code", "error_description": "redacted"}
        )

        with self.assertRaisesRegex(InvalidGitHubCredentialError, "already-used code"):
            self.client.verify_code("one-time-code")


if __name__ == "__main__":
    unittest.main()
