import hmac
import logging
import secrets
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse

from presentation.controllers.auth_controller import AuthController
from presentation.schemas.auth_schema import (
    AuthResponseSchema,
    GoogleSignInSchema,
    LogInSchema,
    SignUpSchema,
)
from presentation.dependencies.auth import get_current_user

logger = logging.getLogger(__name__)


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

    @router.get("/github", include_in_schema=False)
    def start_github_sign_in(request: Request):
        state = secrets.token_urlsafe(32)
        authorization_url = controller.github_authorization_url(state)
        response = RedirectResponse(authorization_url, status_code=status.HTTP_302_FOUND)
        response.set_cookie(
            key="github_oauth_state",
            value=state,
            max_age=600,
            httponly=True,
            secure=request.app.state.github_redirect_uri.startswith("https://"),
            samesite="lax",
            path="/auth/github/callback",
        )
        return response

    @router.get("/github/callback", include_in_schema=False)
    def finish_github_sign_in(
        request: Request,
        code: str | None = Query(default=None),
        state: str | None = Query(default=None),
        oauth_error: str | None = Query(default=None, alias="error"),
    ):
        frontend_url = request.app.state.frontend_url.rstrip("/")
        cookie_state = request.cookies.get("github_oauth_state", "")

        def frontend_result(**values):
            fragment = urlencode(values)
            response = RedirectResponse(
                f"{frontend_url}/#{fragment}", status_code=status.HTTP_303_SEE_OTHER
            )
            response.delete_cookie(
                "github_oauth_state", path="/auth/github/callback"
            )
            return response

        if oauth_error:
            return frontend_result(github_error="authorization_denied")
        if (
            not state
            or not cookie_state
            or not hmac.compare_digest(state, cookie_state)
        ):
            return frontend_result(github_error="invalid_state")
        if not code:
            return frontend_result(github_error="missing_code")

        try:
            auth = controller.authenticate_with_github(code)
        except HTTPException as error:
            # Do not log OAuth codes, state values, or provider access tokens.
            logger.warning(
                "GitHub sign-in callback rejected (HTTP %s): %s",
                error.status_code,
                error.detail,
            )
            return frontend_result(
                github_error="sign_in_failed",
                github_message=str(error.detail),
            )
        logger.info("GitHub sign-in completed; redirecting to the frontend.")
        return frontend_result(
            github_access_token=auth.access_token,
            github_email=auth.email,
            github_id=auth.id,
        )

    @router.get(
        "/session",
        status_code=status.HTTP_200_OK,
        summary="Validate the current session",
    )
    def validate_session(_user_id: str = Depends(get_current_user)):
        return {"authenticated": True}

    return router
