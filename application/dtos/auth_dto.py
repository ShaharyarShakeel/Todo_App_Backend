from dataclasses import dataclass


@dataclass(frozen=True)
class AuthDTO:
    id: str
    email: str
    access_token: str
    token_type: str = "bearer"
