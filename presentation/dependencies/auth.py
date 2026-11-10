#Its job is to check authentication before allowing a request to reach the API's controller.
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from infrastructure.security.auth import TokenService
from application.exceptions import UserRepositoryError
from infrastructure.database.provider_catalog import SUPPORTED_PROVIDERS


bearer_scheme = HTTPBearer(auto_error=False)
token_service = TokenService()


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> str:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    request_token_service = getattr(request.app.state, "token_service", token_service)
    claims = request_token_service.get_claims(credentials.credentials)
    subject = claims.get("sub") if claims else None
    if not isinstance(subject, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    catalog = getattr(request.app.state, "provider_catalog", None)
    registry = getattr(request.app.state, "account_registry", None)
    if catalog is not None and registry is not None:
        token_generation = claims.get("session_generation")
        if (
            isinstance(token_generation, bool)
            or not isinstance(token_generation, int)
            or token_generation != catalog.session_generation
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Access token is no longer valid. Please log in again.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        provider = claims.get("provider")
        try:
            if provider is None:
                # Compatibility for tokens issued before registry-backed identity.
                matches = registry.get_by_provider_user_id(subject)
                if len(matches) != 1:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid or ambiguous access token.",
                        headers={"WWW-Authenticate": "Bearer"},
                    )
                assignment = matches[0]
            else:
                if provider not in SUPPORTED_PROVIDERS:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid access token provider.",
                        headers={"WWW-Authenticate": "Bearer"},
                    )
                assignment = registry.get_by_user_id(subject)
                if assignment is None or assignment.provider != provider:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid account assignment.",
                        headers={"WWW-Authenticate": "Bearer"},
                    )

            if assignment.status != "active":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Account registration is not active.",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            user_repository = catalog.user_repository_for(assignment.provider)
            user = user_repository.get_by_id(assignment.provider_user_id)
            if user is None or user.email.strip().lower() != assignment.email_normalized:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User account no longer exists.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        except UserRepositoryError as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="The assigned account database is temporarily unavailable.",
            ) from error

        catalog.set_request_provider(assignment.provider)
        return assignment.provider_user_id

    # MVC and isolated presentation tests keep their existing JWT-only setup.
    user_repository = getattr(request.app.state, "user_repository", None)
    if user_repository is not None and user_repository.get_by_id(subject) is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account no longer exists.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return subject
