from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from infrastructure.security.auth import TokenService


bearer_scheme = HTTPBearer(auto_error=False)
token_service = TokenService()


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> str:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    subject = token_service.get_subject(credentials.credentials)
    if subject is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # The onion app installs its selected UserRepository on app.state. MVC uses
    # this shared dependency too, but keeps its existing JWT-only behavior.
    user_repository = getattr(request.app.state, "user_repository", None)
    if user_repository is not None and user_repository.get_by_id(subject) is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account no longer exists.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return subject
