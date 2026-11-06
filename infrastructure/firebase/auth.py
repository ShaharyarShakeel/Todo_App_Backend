from typing import Optional

import firebase_admin
from firebase_admin import auth, exceptions


def get_firebase_subject(token: str) -> Optional[str]:
    """Verify a Firebase client ID token and return its UID, if valid."""
    try:
        decoded_token = auth.verify_id_token(token, app=firebase_admin.get_app())
    except (ValueError, exceptions.FirebaseError):
        return None

    subject = decoded_token.get("uid")
    return subject if isinstance(subject, str) and subject else None
