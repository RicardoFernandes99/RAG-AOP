from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user
from app.schemas.auth import AuthUserResponse
from app.services.auth_service import AuthUser

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me", response_model=AuthUserResponse)
def get_current_user_profile(current_user: AuthUser = Depends(get_current_user)) -> AuthUserResponse:
    return AuthUserResponse(id=current_user.id, username=current_user.username)
