import json
import uuid
from dataclasses import dataclass

from app.services.chat_service import RetrievedDocument
from app.services.db_service import get_connection


@dataclass
class StoredMessage:
    id: int
    role: str
    content: str
    persona: str | None
    sources: list[str]
    context: list[RetrievedDocument]
    created_at: str


@dataclass
class StoredConversation:
    id: str
    title: str
    updated_at: str
    messages: list[StoredMessage]


def _default_title(question: str | None = None) -> str:
    normalized = (question or "").strip()
    return normalized[:30] or "New conversation"


def create_conversation(user_id: int, title: str | None = None) -> StoredConversation:
    conversation_id = str(uuid.uuid4())
    conversation_title = _default_title(title)

    with get_connection() as connection:
        connection.execute(
            "INSERT INTO conversations (id, user_id, title) VALUES (?, ?, ?)",
            (conversation_id, user_id, conversation_title),
        )
        row = connection.execute(
            "SELECT id, title, updated_at FROM conversations WHERE id = ?",
            (conversation_id,),
        ).fetchone()

    return StoredConversation(
        id=row["id"],
        title=row["title"],
        updated_at=row["updated_at"],
        messages=[],
    )


def ensure_conversation(user_id: int, conversation_id: str | None, first_question: str) -> StoredConversation:
    if conversation_id:
        conversation = get_conversation(user_id, conversation_id)
        if conversation is None:
            raise ValueError("Conversation not found.")
        return conversation

    return create_conversation(user_id, first_question)


def list_conversations(user_id: int) -> list[StoredConversation]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, title, updated_at
            FROM conversations
            WHERE user_id = ?
            ORDER BY updated_at DESC, created_at DESC
            """,
            (user_id,),
        ).fetchall()

    return [
        StoredConversation(
            id=row["id"],
            title=row["title"],
            updated_at=row["updated_at"],
            messages=[],
        )
        for row in rows
    ]


def get_conversation(user_id: int, conversation_id: str) -> StoredConversation | None:
    with get_connection() as connection:
        conversation_row = connection.execute(
            """
            SELECT id, title, updated_at
            FROM conversations
            WHERE id = ? AND user_id = ?
            """,
            (conversation_id, user_id),
        ).fetchone()

        if conversation_row is None:
            return None

        message_rows = connection.execute(
            """
            SELECT id, role, content, persona, sources_json, context_json, created_at
            FROM messages
            WHERE conversation_id = ?
            ORDER BY id ASC
            """,
            (conversation_id,),
        ).fetchall()

    return StoredConversation(
        id=conversation_row["id"],
        title=conversation_row["title"],
        updated_at=conversation_row["updated_at"],
        messages=[_map_message_row(row) for row in message_rows],
    )


def append_message(
    conversation_id: str,
    role: str,
    content: str,
    persona: str | None = None,
    sources: list[str] | None = None,
    context: list[RetrievedDocument] | None = None,
) -> StoredMessage:
    serialized_sources = json.dumps(sources or [])
    serialized_context = json.dumps(
        [
            {
                "source": document.source,
                "page": document.page,
                "content": document.content,
            }
            for document in (context or [])
        ]
    )

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO messages (conversation_id, role, content, persona, sources_json, context_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (conversation_id, role, content, persona, serialized_sources, serialized_context),
        )
        connection.execute(
            """
            UPDATE conversations
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (conversation_id,),
        )
        row = connection.execute(
            """
            SELECT id, role, content, persona, sources_json, context_json, created_at
            FROM messages
            WHERE id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()

    return _map_message_row(row)


def update_conversation_title(conversation_id: str, title: str) -> None:
    normalized_title = _default_title(title)
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE conversations
            SET title = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (normalized_title, conversation_id),
        )


def _map_message_row(row) -> StoredMessage:
    sources = json.loads(row["sources_json"] or "[]")
    context_items = json.loads(row["context_json"] or "[]")
    return StoredMessage(
        id=row["id"],
        role=row["role"],
        content=row["content"],
        persona=row["persona"],
        sources=sources,
        context=[
            RetrievedDocument(
                source=item["source"],
                page=item.get("page"),
                content=item["content"],
            )
            for item in context_items
        ],
        created_at=row["created_at"],
    )
