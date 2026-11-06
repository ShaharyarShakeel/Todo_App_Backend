from fastapi import HTTPException, status

from infrastructure.security.auth import PasswordHasher, TokenService
from mvc.exceptions import UserAlreadyExistsError, UserStorageError
from mvc.models.user_model import UserModel
from mvc.views.auth_view import AuthView, LogInView, SignUpView


class AuthController:
    password_hasher = PasswordHasher()
    token_service = TokenService()

    @staticmethod
    def sign_up(payload: SignUpView):
        email = payload.email.strip().lower()
        try:
            if UserModel.find_by_email(email) is not None:
                raise UserAlreadyExistsError(
                    "An account with this email already exists."
                )
            user = UserModel.create(
                email=email,
                password_hash=AuthController.password_hasher.hash(payload.password),
            )
            token = AuthController.token_service.create_access_token(str(user.id))
            return AuthView.render_auth(user, token)
        except UserAlreadyExistsError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(error),
            ) from error
        except UserStorageError as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="User storage is temporarily unavailable.",
            ) from error

    @staticmethod
    def log_in(payload: LogInView):
        try:
            user = UserModel.find_by_email(payload.email)
        except UserStorageError as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="User storage is temporarily unavailable.",
            ) from error

        if user is None or not AuthController.password_hasher.verify(
            payload.password, user.password_hash
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email or password is incorrect.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = AuthController.token_service.create_access_token(str(user.id))
        return AuthView.render_auth(user, token)
