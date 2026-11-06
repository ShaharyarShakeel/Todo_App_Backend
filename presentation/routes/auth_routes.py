from fastapi import APIRouter, status

from presentation.controllers.auth_controller import AuthController
from presentation.schemas.auth_schema import (
    AuthResponseSchema,
    LogInSchema,
    SignUpSchema,
)


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

    return router
