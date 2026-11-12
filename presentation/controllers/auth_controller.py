from fastapi import HTTPException, status

from application.exceptions import (
    GoogleAccountLinkRequiredError,
    GoogleIdentityProviderUnavailableError,
    GoogleSignInConfigurationError,
    InvalidGoogleCredentialError,
    InvalidCredentialsError,
    UserAlreadyExistsError,
    UserRepositoryError,
)
from application.use_cases.log_in import LogIn
from application.use_cases.google_sign_in import GoogleSignIn
from application.use_cases.sign_up import SignUp
from presentation.schemas.auth_schema import LogInSchema, SignUpSchema


class AuthController:
    def __init__(self, sign_up: SignUp, log_in: LogIn, google_sign_in: GoogleSignIn = None):
        self.sign_up = sign_up
        self.log_in = log_in
        self.google_sign_in = google_sign_in

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

    def authenticate_with_google(self, credential: str):
        if self.google_sign_in is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Google sign-in is not configured.",
            )
        try:
            return self.google_sign_in.execute(credential)
        except InvalidGoogleCredentialError as error:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(error),
                headers={"WWW-Authenticate": "Bearer"},
            ) from error
        except GoogleAccountLinkRequiredError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(error),
            ) from error
        except (GoogleSignInConfigurationError, GoogleIdentityProviderUnavailableError) as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(error),
            ) from error
        except (InvalidCredentialsError, UserAlreadyExistsError) as error:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google account could not be authenticated in the selected database.",
                headers={"WWW-Authenticate": "Bearer"},
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
