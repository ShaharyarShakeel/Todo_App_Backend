from fastapi import HTTPException, status

from application.exceptions import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
    UserRepositoryError,
)
from application.use_cases.log_in import LogIn
from application.use_cases.sign_up import SignUp
from presentation.schemas.auth_schema import LogInSchema, SignUpSchema


class AuthController:
    def __init__(self, sign_up: SignUp, log_in: LogIn):
        self.sign_up = sign_up
        self.log_in = log_in

    def register(self, data: SignUpSchema):
        try:
            return self.sign_up.execute(data.email, data.password)
        except UserAlreadyExistsError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(error),
            ) from error
        except UserRepositoryError as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="User storage is temporarily unavailable.",
            ) from error

    def authenticate(self, data: LogInSchema):
        try:
            return self.log_in.execute(data.email, data.password)
        except InvalidCredentialsError as error:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(error),
                headers={"WWW-Authenticate": "Bearer"},
            ) from error
        except UserRepositoryError as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="User storage is temporarily unavailable.",
            ) from error
