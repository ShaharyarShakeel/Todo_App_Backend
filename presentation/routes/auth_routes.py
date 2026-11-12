from fastapi import APIRouter, Depends, status

from presentation.controllers.auth_controller import AuthController
from presentation.schemas.auth_schema import (
    AuthResponseSchema,
    GoogleSignInSchema,
    LogInSchema,
    SignUpSchema,
)
from presentation.dependencies.auth import get_current_user


def create_auth_routes(controller: AuthController) -> APIRouter:
    router = APIRouter(prefix="/auth", tags=["Authentication"])

    @router.post(
        "/signup",
        response_model=AuthResponseSchema,
        status_code=status.HTTP_201_CREATED,
        summary="Create an account",
    )
    def sign_up(data: SignUpSchema):
        return controller.register(data)

    @router.post(
        "/login",
        response_model=AuthResponseSchema,
        status_code=status.HTTP_200_OK,
        summary="Log in and receive an access token",
    )
    def log_in(data: LogInSchema):
        return controller.authenticate(data)

    @router.post(
        "/google",
        response_model=AuthResponseSchema,
        status_code=status.HTTP_200_OK,
        summary="Sign in with Google",
    )
    def google_sign_in(data: GoogleSignInSchema):
        return controller.authenticate_with_google(data.credential)

    @router.get(
        "/session",
        status_code=status.HTTP_200_OK,
        summary="Validate the current session",
    )
    def validate_session(_user_id: str = Depends(get_current_user)):
        return {"authenticated": True}

    return router
