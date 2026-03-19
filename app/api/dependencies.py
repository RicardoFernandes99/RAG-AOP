from fastapi import Cookie, HTTPException, status

from app.core.config import SESSION_COOKIE_NAME
from app.services.auth_service import AuthUser, get_user_by_session


def get_optional_user(
    session_id: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> AuthUser | None:
    return get_user_by_session(session_id)


def get_current_user(
    session_id: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> AuthUser:
    user = get_user_by_session(session_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )
    return user
