from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import db_service
from app.services.chat_service import ChatResponse, RetrievedDocument


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(db_service, "SQLITE_DB_PATH", tmp_path / "test_app.sqlite3")
    with TestClient(app) as test_client:
        yield test_client


def register(client: TestClient, username: str = "ricardo", password: str = "secret"):
    return client.post(
        "/api/auth/register",
        json={"username": username, "password": password},
    )


def test_index_serves_frontend(client: TestClient):
    response = client.get("/")

    assert response.status_code == 200
    assert "AccountantGPT" in response.text


def test_register_login_logout_and_status(client: TestClient):
    register_response = register(client)

    assert register_response.status_code == 201
    assert register_response.json() == {
        "authenticated": True,
        "user": {"id": 1, "username": "ricardo"},
    }

    status_response = client.get("/api/auth/status")
    assert status_response.status_code == 200
    assert status_response.json()["authenticated"] is True

    logout_response = client.post("/api/auth/logout")
    assert logout_response.status_code == 204

    logged_out_status = client.get("/api/auth/status")
    assert logged_out_status.json() == {"authenticated": False, "user": None}

    login_response = client.post(
        "/api/auth/login",
        json={"username": "ricardo", "password": "secret"},
    )
    assert login_response.status_code == 200
    assert login_response.json()["user"]["username"] == "ricardo"


def test_chat_endpoint_requires_authentication(client: TestClient):
    response = client.post("/api/chat", json={"question": "Pergunta"})

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required."}


def test_chat_endpoint_returns_response(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    def fake_answer_question(_: str) -> ChatResponse:
        return ChatResponse(
            answer="Resposta",
            sources=["dl_snc_anexo.pdf"],
            retrieved_documents=[
                RetrievedDocument(
                    source="dl_snc_anexo.pdf",
                    page=1,
                    content="Conteudo",
                )
            ],
        )

    monkeypatch.setattr("app.api.routes.chat.answer_question", fake_answer_question)
    register(client)

    conversation_response = client.post("/api/chat/conversations")
    conversation_id = conversation_response.json()["id"]

    response = client.post(
        "/api/chat",
        json={"question": "Pergunta", "conversation_id": conversation_id},
    )

    assert response.status_code == 200
    assert response.json() == {
        "conversation_id": conversation_id,
        "answer": "Resposta",
        "sources": ["dl_snc_anexo.pdf"],
        "retrieved_documents": [
            {
                "source": "dl_snc_anexo.pdf",
                "page": 1,
                "content": "Conteudo",
            }
        ],
    }

    stored_conversation = client.get(f"/api/chat/conversations/{conversation_id}")
    assert stored_conversation.status_code == 200
    assert [message["role"] for message in stored_conversation.json()["messages"]] == [
        "user",
        "assistant",
    ]


def test_chat_endpoint_rejects_empty_input(client: TestClient):
    register(client)
    conversation_id = client.post("/api/chat/conversations").json()["id"]
    response = client.post(
        "/api/chat",
        json={"question": "", "conversation_id": conversation_id},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Question cannot be empty."}


def test_chat_endpoint_handles_backend_failure(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    def failing_answer_question(_: str) -> ChatResponse:
        raise RuntimeError("The chat backend is unavailable.")

    monkeypatch.setattr("app.api.routes.chat.answer_question", failing_answer_question)
    register(client)
    conversation_id = client.post("/api/chat/conversations").json()["id"]

    response = client.post(
        "/api/chat",
        json={"question": "Pergunta", "conversation_id": conversation_id},
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "The chat backend is unavailable."}


def test_chat_stream_endpoint_returns_metadata_and_chunks(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    def fake_stream_answer_question(_: str):
        documents = [
            RetrievedDocument(
                source="dl_snc_anexo.pdf",
                page=2,
                content="Conteudo de contexto",
            )
        ]

        def generator():
            yield "Res"
            yield "posta"

        return documents, generator()

    monkeypatch.setattr("app.api.routes.chat.stream_answer_question", fake_stream_answer_question)
    register(client)
    conversation_id = client.post("/api/chat/conversations").json()["id"]

    with client.stream(
        "POST",
        "/api/chat/stream",
        json={"question": "Pergunta", "conversation_id": conversation_id},
    ) as response:
        body = b"".join(response.iter_bytes()).decode()

    lines = [line for line in body.splitlines() if line]

    assert response.status_code == 200
    assert '"type": "metadata"' in lines[0]
    assert f'"conversation_id": "{conversation_id}"' in lines[0]
    assert '"type": "chunk"' in lines[1]
    assert '"type": "complete"' in lines[-1]
