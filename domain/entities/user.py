from typing import Optional


class User:
    def __init__(self, email: str, password_hash: str, user_id: Optional[str] = None):
        self.id = user_id
        self.email = email.strip().lower()
        self.password_hash = password_hash
