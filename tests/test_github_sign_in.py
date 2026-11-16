import unittest
from dataclasses import replace

from application.dtos.verified_github_identity import VerifiedGitHubIdentity
from application.use_cases.github_sign_in import GitHubSignIn
from domain.entities.account_assignment import AccountAssignment
from domain.entities.user import User


class MemoryGithubRegistry:
    def __init__(self):
        self.by_id = {}

    def reserve(self, assignment):
        self.by_id[assignment.user_id] = replace(assignment, status="pending")

    def activate(self, user_id):
        self.by_id[user_id] = replace(self.by_id[user_id], status="active")

    def delete_pending(self, user_id):
        self.by_id.pop(user_id, None)

    def get_by_github_sub(self, subject, provider):
        return next(
            (
                item
                for item in self.by_id.values()
                if item.github_sub == subject and item.provider == provider
            ),
            None,
        )

    def get_by_email(self, email, provider):
        return next(
            (
                item
                for item in self.by_id.values()
                if item.email_normalized == email and item.provider == provider
            ),
            None,
        )

    def set_github_sub(self, user_id, provider, subject):
        item = self.by_id[user_id]
        if item.provider != provider:
            raise AssertionError("GitHub identity was assigned in the wrong provider")
        self.by_id[user_id] = replace(item, github_sub=subject)


class MemoryUserRepository:
    def __init__(self):
        self.users = {}

    def new_user_id(self, email):
        return "provider-user-id"

    def create(self, user):
        self.users[user.id] = user
        return user

    def get_by_id(self, user_id):
        return self.users.get(user_id)


class StubCatalog:
    def __init__(self, repository):
        self.repository = repository

    def registration_context(self):
        return "postgresql", 12

    def user_repository_for(self, provider):
        if provider != "postgresql":
            raise AssertionError("The sign-in searched a non-selected provider")
        return self.repository


class StubIdentityProvider:
    def verify_code(self, code):
        if code != "valid-code":
            raise AssertionError("Unexpected OAuth code")
        return VerifiedGitHubIdentity("github-account-123", "person@example.com")

    def authorization_url(self, state):
        return f"https://github.com/?state={state}"


class StubPasswordHasher:
    def hash(self, password):
        return "hashed-random-password"


class StubTokenService:
    def __init__(self):
        self.claims = None

    def create_access_token(self, subject, provider, session_generation):
        self.claims = (subject, provider, session_generation)
        return "app-jwt"


class TestGitHubSignIn(unittest.TestCase):
    def setUp(self):
        self.registry = MemoryGithubRegistry()
        self.users = MemoryUserRepository()
        self.tokens = StubTokenService()
        self.use_case = GitHubSignIn(
            registry=self.registry,
            provider_catalog=StubCatalog(self.users),
            token_service=self.tokens,
            password_hasher=StubPasswordHasher(),
            identity_provider=StubIdentityProvider(),
        )

    def test_creates_account_in_selected_provider_and_reuses_github_assignment(self):
        first = self.use_case.execute("valid-code")
        assignment = self.registry.get_by_github_sub("github-account-123", "postgresql")
        second = self.use_case.execute("valid-code")

        self.assertEqual(first.access_token, "app-jwt")
        self.assertEqual(second.id, assignment.user_id)
        self.assertEqual(assignment.status, "active")
        self.assertEqual(assignment.provider, "postgresql")
        self.assertEqual(len(self.users.users), 1)
        self.assertEqual(self.tokens.claims, (assignment.user_id, "postgresql", 12))

    def test_links_matching_existing_email_account_with_verified_github_identity(self):
        assignment = AccountAssignment(
            user_id="global-id",
            email_normalized="person@example.com",
            provider="postgresql",
            provider_user_id="provider-user-id",
        )
        self.registry.reserve(assignment)
        self.registry.activate(assignment.user_id)
        self.users.create(
            User("person@example.com", "existing-hash", "provider-user-id")
        )

        result = self.use_case.execute("valid-code")

        self.assertEqual(result.id, "global-id")
        self.assertEqual(
            self.registry.get_by_github_sub("github-account-123", "postgresql").user_id,
            "global-id",
        )
        self.assertEqual(len(self.users.users), 1)


if __name__ == "__main__":
    unittest.main()
