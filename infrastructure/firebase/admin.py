from pathlib import Path
from typing import Optional

import firebase_admin
from firebase_admin import credentials

from infrastructure.config.settings import settings


_app: Optional[firebase_admin.App] = None


def initialize_firebase() -> firebase_admin.App:
    """Initialize the Firebase Admin SDK once using the configured service account."""
    global _app
    if _app is not None:
        return _app

    credential_path = Path(settings.FIREBASE_CREDENTIALS_PATH).expanduser()
    if not credential_path.is_file():
        raise FileNotFoundError(
            "Firebase service account file not found. Set GOOGLE_APPLICATION_CREDENTIALS "
            "to the path of your service account JSON."
        )

    try:
        _app = firebase_admin.get_app()
    except ValueError:
        _app = firebase_admin.initialize_app(
            credentials.Certificate(str(credential_path))
        )
    return _app


def close_firebase() -> None:
    """Release the initialized Firebase Admin app during application shutdown."""
    global _app
    if _app is not None:
        firebase_admin.delete_app(_app)
        _app = None
