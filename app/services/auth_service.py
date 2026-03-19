import secrets
from dataclasses import dataclass

from app.services.db_service import get_connection


@dataclass
class AuthUser:
    id: int
    username: str


def _normalize_username(username: str) -> str:
    normalized = username.strip()
    if not normalized:
        raise ValueError("Username is required.")
    return normalized


def _normalize_password(password: str) -> str:
    normalized = password.strip()
    if not normalized:
        raise ValueError("Password is required.")
    return normalized


def create_user(username: str, password: str) -> AuthUser:
    normalized_username = _normalize_username(username)
    normalized_password = _normalize_password(password)

    with get_connection() as connection:
        existing_user = connection.execute(
            "SELECT id FROM users WHERE username = ?",
            (normalized_username,),
        ).fetchone()
        if existing_user:
            raise ValueError("Username already exists.")

        cursor = connection.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (normalized_username, normalized_password),
        )
        user_id = cursor.lastrowid

    return AuthUser(id=user_id, username=normalized_username)


def authenticate_user(username: str, password: str) -> AuthUser:
    normalized_username = _normalize_username(username)
    normalized_password = _normalize_password(password)

    with get_connection() as connection:
        row = connection.execute(
            "SELECT id, username, password FROM users WHERE username = ?",
            (normalized_username,),
        ).fetchone()

    if row is None or row["password"] != normalized_password:
        raise ValueError("Invalid username or password.")

    return AuthUser(id=row["id"], username=row["username"])


def create_session(user_id: int) -> str:
    session_id = secrets.token_urlsafe(32)
    with get_connection() as connection:
        connection.execute(
            "INSERT INTO sessions (id, user_id) VALUES (?, ?)",
            (session_id, user_id),
        )
    return session_id


def delete_session(session_id: str) -> None:
    with get_connection() as connection:
        connection.execute("DELETE FROM sessions WHERE id = ?", (session_id,))


def get_user_by_session(session_id: str | None) -> AuthUser | None:
    if not session_id:
        return None

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT users.id, users.username
            FROM sessions
            INNER JOIN users ON users.id = sessions.user_id
            WHERE sessions.id = ?
            """,
            (session_id,),
        ).fetchone()

    if row is None:
        return None

    return AuthUser(id=row["id"], username=row["username"])
