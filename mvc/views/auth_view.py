from typing import Dict

from pydantic import BaseModel, Field


class SignUpView(BaseModel):
    email: str = Field(
        min_length=3,
        max_length=254,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    )
    password: str = Field(min_length=8, max_length=128)


class LogInView(BaseModel):
    email: str = Field(
        min_length=3,
        max_length=254,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    )
    password: str = Field(min_length=8, max_length=128)


class AuthResponseView(BaseModel):
    id: str
    email: str
    access_token: str
    token_type: str = "bearer"


class AuthView:
    @staticmethod
    def render_auth(user, access_token: str) -> Dict[str, str]:
        return {
            "id": user.id,
            "email": user.email,
            "access_token": access_token,
            "token_type": "bearer",
        }
