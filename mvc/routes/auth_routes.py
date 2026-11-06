from fastapi import APIRouter, status

from mvc.controllers.auth_controller import AuthController
from mvc.views.auth_view import AuthResponseView, LogInView, SignUpView


router = APIRouter(prefix="/auth", tags=["MVC Authentication"])


@router.post(
    "/signup",
    response_model=AuthResponseView,
    status_code=status.HTTP_201_CREATED,
    summary="[MVC] Create an account",
)
def sign_up(payload: SignUpView):
    return AuthController.sign_up(payload)


@router.post(
    "/login",
    response_model=AuthResponseView,
    status_code=status.HTTP_200_OK,
    summary="[MVC] Log in and receive an access token",
)
def log_in(payload: LogInView):
    return AuthController.log_in(payload)
