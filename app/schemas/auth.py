from pydantic import BaseModel, Field


class CredentialsRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=255)


class AuthUserResponse(BaseModel):
    id: int
    username: str


class AuthStatusResponse(BaseModel):
    authenticated: bool
    user: AuthUserResponse | None = None
