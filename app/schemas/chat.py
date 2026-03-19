from pydantic import BaseModel


class ChatRequest(BaseModel):
    question: str
    conversation_id: str | None = None
    persona: str = "accountant"


class RetrievedDocumentResponse(BaseModel):
    source: str
    page: int | None
    content: str


class ChatApiResponse(BaseModel):
    conversation_id: str
    answer: str
    sources: list[str]
    retrieved_documents: list[RetrievedDocumentResponse]


class ConversationSummaryResponse(BaseModel):
    id: str
    title: str
    updated_at: str


class ChatMessageResponse(BaseModel):
    id: int
    role: str
    content: str
    persona: str | None = None
    sources: list[str] = []
    context: list[RetrievedDocumentResponse] = []
    created_at: str


class ConversationDetailResponse(BaseModel):
    id: str
    title: str
    updated_at: str
    messages: list[ChatMessageResponse]
