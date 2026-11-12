import unittest
from unittest.mock import patch

from application.exceptions import (
    GoogleSignInConfigurationError,
    InvalidGoogleCredentialError,
)
from infrastructure.security.google_identity_verifier import GoogleIdentityVerifierAdapter


class TestGoogleIdentityVerifierAdapter(unittest.TestCase):
    @patch("infrastructure.security.google_identity_verifier.id_token.verify_oauth2_token")
    def test_verifies_with_configured_audience_and_returns_normalized_identity(self, verify):
        verify.return_value = {
            "sub": "google-sub",
            "email": "Person@GMAIL.com",
            "email_verified": True,
        }
        identity = GoogleIdentityVerifierAdapter("web-client-id").verify("id-token")

        self.assertEqual(identity.subject, "google-sub")
        self.assertEqual(identity.email, "person@gmail.com")
        self.assertTrue(identity.email_is_authoritative)
        self.assertEqual(verify.call_args.args[0], "id-token")
        self.assertEqual(verify.call_args.kwargs["audience"], "web-client-id")

    @patch("infrastructure.security.google_identity_verifier.id_token.verify_oauth2_token")
    def test_rejects_unverified_email(self, verify):
        verify.return_value = {
            "sub": "google-sub",
            "email": "person@example.net",
            "email_verified": False,
        }
        with self.assertRaises(InvalidGoogleCredentialError):
            GoogleIdentityVerifierAdapter("web-client-id").verify("id-token")

    def test_requires_a_configured_client_id(self):
        with self.assertRaises(GoogleSignInConfigurationError):
            GoogleIdentityVerifierAdapter("").verify("id-token")


if __name__ == "__main__":
    unittest.main()
