from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.api.dependencies import get_optional_user
from app.core.config import SESSION_COOKIE_NAME, SESSION_MAX_AGE_SECONDS
from app.schemas.auth import AuthStatusResponse, AuthUserResponse, CredentialsRequest
from app.services.auth_service import AuthUser, authenticate_user, create_session, create_user, delete_session

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _build_auth_response(user: AuthUser) -> AuthStatusResponse:
    return AuthStatusResponse(
        authenticated=True,
        user=AuthUserResponse(id=user.id, username=user.username),
    )


def _set_session_cookie(response: Response, session_id: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        httponly=True,
        samesite="lax",
        max_age=SESSION_MAX_AGE_SECONDS,
    )


@router.get("/status", response_model=AuthStatusResponse)
def auth_status(current_user: AuthUser | None = Depends(get_optional_user)) -> AuthStatusResponse:
    if current_user is None:
        return AuthStatusResponse(authenticated=False, user=None)
    return _build_auth_response(current_user)


@router.post("/register", response_model=AuthStatusResponse, status_code=status.HTTP_201_CREATED)
def register(payload: CredentialsRequest, response: Response) -> AuthStatusResponse:
    try:
        user = create_user(payload.username, payload.password)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    session_id = create_session(user.id)
    _set_session_cookie(response, session_id)
    return _build_auth_response(user)


@router.post("/login", response_model=AuthStatusResponse)
def login(payload: CredentialsRequest, response: Response) -> AuthStatusResponse:
    try:
        user = authenticate_user(payload.username, payload.password)
    except ValueError as error:
        raise HTTPException(status_code=401, detail=str(error)) from error

    session_id = create_session(user.id)
    _set_session_cookie(response, session_id)
    return _build_auth_response(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    current_user: AuthUser | None = Depends(get_optional_user),
) -> Response:
    if current_user is not None:
        delete_session(request.cookies.get(SESSION_COOKIE_NAME))
    response.delete_cookie(key=SESSION_COOKIE_NAME)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response
