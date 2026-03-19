import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.api.dependencies import get_current_user
from app.schemas.chat import (
    ChatApiResponse,
    ChatMessageResponse,
    ChatRequest,
    ConversationDetailResponse,
    ConversationSummaryResponse,
    RetrievedDocumentResponse,
)
from app.services.chat_service import (
    ChatResponse,
    RetrievedDocument,
    answer_question,
    stream_answer_question,
)
from app.services.auth_service import AuthUser
from app.services.conversation_service import (
    append_message,
    create_conversation,
    ensure_conversation,
    get_conversation,
    list_conversations,
    update_conversation_title,
)

router = APIRouter(prefix="/api/chat", tags=["chat"])


def _to_document_response(document: RetrievedDocument) -> RetrievedDocumentResponse:
    return RetrievedDocumentResponse(
        source=document.source,
        page=document.page,
        content=document.content,
    )


def _to_api_response(conversation_id: str, response: ChatResponse) -> ChatApiResponse:
    return ChatApiResponse(
        conversation_id=conversation_id,
        answer=response.answer,
        sources=response.sources,
        retrieved_documents=[_to_document_response(document) for document in response.retrieved_documents],
    )


def _to_message_response(message) -> ChatMessageResponse:
    return ChatMessageResponse(
        id=message.id,
        role=message.role,
        content=message.content,
        persona=message.persona,
        sources=message.sources,
        context=[_to_document_response(document) for document in message.context],
        created_at=message.created_at,
    )


@router.get("/conversations", response_model=list[ConversationSummaryResponse])
def get_conversations(
    current_user: AuthUser = Depends(get_current_user),
) -> list[ConversationSummaryResponse]:
    return [
        ConversationSummaryResponse(
            id=conversation.id,
            title=conversation.title,
            updated_at=conversation.updated_at,
        )
        for conversation in list_conversations(current_user.id)
    ]


@router.post("/conversations", response_model=ConversationDetailResponse)
def new_conversation(
    current_user: AuthUser = Depends(get_current_user),
) -> ConversationDetailResponse:
    conversation = create_conversation(current_user.id)
    return ConversationDetailResponse(
        id=conversation.id,
        title=conversation.title,
        updated_at=conversation.updated_at,
        messages=[],
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
def get_conversation_detail(
    conversation_id: str,
    current_user: AuthUser = Depends(get_current_user),
) -> ConversationDetailResponse:
    conversation = get_conversation(current_user.id, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    return ConversationDetailResponse(
        id=conversation.id,
        title=conversation.title,
        updated_at=conversation.updated_at,
        messages=[_to_message_response(message) for message in conversation.messages],
    )


@router.post("", response_model=ChatApiResponse)
def chat(payload: ChatRequest, current_user: AuthUser = Depends(get_current_user)) -> ChatApiResponse:
    try:
        conversation = ensure_conversation(
            current_user.id,
            payload.conversation_id,
            payload.question,
        )
        response = answer_question(payload.question, payload.persona)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    append_message(conversation.id, "user", payload.question)
    append_message(
        conversation.id,
        "assistant",
        response.answer,
        persona=payload.persona,
        sources=response.sources,
        context=response.retrieved_documents,
    )
    update_conversation_title(conversation.id, payload.question)
    return _to_api_response(conversation.id, response)


@router.post("/stream")
def chat_stream(
    payload: ChatRequest,
    current_user: AuthUser = Depends(get_current_user),
) -> StreamingResponse:
    try:
        conversation = ensure_conversation(
            current_user.id,
            payload.conversation_id,
            payload.question,
        )
        retrieved_documents, stream = stream_answer_question(
            payload.question,
            payload.persona,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    sources = list(dict.fromkeys(document.source for document in retrieved_documents))

    def event_stream():
        yield json.dumps(
            {
                "type": "metadata",
                "conversation_id": conversation.id,
                "sources": sources,
                "retrieved_documents": [
                    {
                        "source": document.source,
                        "page": document.page,
                        "content": document.content,
                    }
                    for document in retrieved_documents
                ],
            }
        ) + "\n"

        chunks: list[str] = []
        try:
            for chunk in stream:
                chunks.append(chunk)
                yield json.dumps({"type": "chunk", "content": chunk}) + "\n"
        except Exception as error:
            yield json.dumps({"type": "error", "detail": str(error)}) + "\n"
            return

        answer = "".join(chunks).strip()
        append_message(conversation.id, "user", payload.question)
        append_message(
            conversation.id,
            "assistant",
            answer,
            persona=payload.persona,
            sources=sources,
            context=retrieved_documents,
        )
        update_conversation_title(conversation.id, payload.question)

        yield json.dumps({"type": "complete", "conversation_id": conversation.id, "answer": answer}) + "\n"

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")
