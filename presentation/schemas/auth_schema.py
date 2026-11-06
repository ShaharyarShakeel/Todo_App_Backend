from pydantic import BaseModel, Field


class SignUpSchema(BaseModel):
    email: str = Field(
        min_length=3,
        max_length=254,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    )
    password: str = Field(min_length=8, max_length=128)


class LogInSchema(BaseModel):
    email: str = Field(
        min_length=3,
        max_length=254,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    )
    password: str = Field(min_length=8, max_length=128)


class AuthResponseSchema(BaseModel):
    id: str
    email: str
    access_token: str
    token_type: str = "bearer"
