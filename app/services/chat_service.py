from dataclasses import dataclass
from typing import Any, Iterator

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import OllamaLLM

from app.core.config import OLLAMA_BASE_URL, OLLAMA_CHAT_MODEL

ACCOUNTANT_PERSONA = "accountant"
AI_PERSONA = "ai"


@dataclass
class RetrievedDocument:
    source: str
    page: int | None
    content: str


@dataclass
class ChatResponse:
    answer: str
    sources: list[str]
    retrieved_documents: list[RetrievedDocument]


def _normalize_source_name(source: str) -> str:
    return source.split("\\")[-1].split("/")[-1]


def serialize_document(document: Document) -> RetrievedDocument:
    source = document.metadata.get("source", "unknown")
    page = document.metadata.get("page")
    return RetrievedDocument(
        source=_normalize_source_name(source),
        page=page,
        content=document.page_content,
    )


def format_documents(documents: list[Document]) -> str:
    formatted_chunks = []

    for document in documents:
        serialized = serialize_document(document)
        formatted_chunks.append(
            f"Document: {serialized.source}\n"
            f"Page: {serialized.page}\n"
            f"Content: {serialized.content}"
        )

    return "\n\n".join(formatted_chunks)


ACCOUNTANT_TEMPLATE = """
You are an expert accountant specialized in Portuguese accounting rules.

Use the provided documents and retrieved context as your main source of information.
Check the documents carefully before answering, and rely on them whenever possible.
If the documents are insufficient, you may use your own general accounting knowledge,
but clearly distinguish what is supported by the documents from what is general knowledge or inference.

Documents:
{documents}

Question:
{question}

Respond in the same language as the question, and be as helpful, clear, and accurate as possible.
If the language is Portuguese, respond in Portuguese from Portugal.
"""

AI_TEMPLATE = """
You are AI Assistant, a general-purpose AI bot.

Be as helpful, clear, and accurate as possible using your own knowledge.
If you are uncertain, say so clearly instead of guessing.

Question:
{question}

Respond in the same language as the question, and be as helpful, clear, and accurate as possible.
If the language is Portuguese, respond in Portuguese from Portugal.
"""

_retriever: Any | None = None
_chains: dict[str, Any] = {}


def get_retriever() -> Any:
    global _retriever
    if _retriever is None:
        from app.services.vector_service import retriever

        _retriever = retriever

    return _retriever


def get_chain(persona: str = ACCOUNTANT_PERSONA) -> Any:
    if persona not in _chains:
        model = OllamaLLM(
            model=OLLAMA_CHAT_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0.2,
            top_p=0.9,
            num_predict=2048,
            top_k=40,
            seed=42,
        )
        template = ACCOUNTANT_TEMPLATE if persona == ACCOUNTANT_PERSONA else AI_TEMPLATE
        _chains[persona] = ChatPromptTemplate.from_template(template) | model

    return _chains[persona]


def _normalize_persona(persona: str | None) -> str:
    normalized = (persona or ACCOUNTANT_PERSONA).strip().lower()
    if normalized not in {ACCOUNTANT_PERSONA, AI_PERSONA}:
        raise ValueError("Invalid chat persona.")
    return normalized


def _prepare_question(
    question: str,
    persona: str,
) -> tuple[str, list[Document], list[RetrievedDocument]]:
    normalized_question = question.strip()
    if not normalized_question:
        raise ValueError("Question cannot be empty.")

    if persona == AI_PERSONA:
        return normalized_question, [], []

    try:
        documents = get_retriever().invoke(normalized_question)
    except FileNotFoundError as error:
        raise RuntimeError(str(error)) from error
    except ValueError:
        raise
    except Exception as error:
        raise RuntimeError("The document retriever is unavailable.") from error

    retrieved_documents = [serialize_document(document) for document in documents]
    return normalized_question, documents, retrieved_documents


def answer_question(
    question: str,
    persona: str = ACCOUNTANT_PERSONA,
) -> ChatResponse:
    normalized_persona = _normalize_persona(persona)
    normalized_question, documents, retrieved_documents = _prepare_question(
        question,
        normalized_persona,
    )

    try:
        formatted_documents = format_documents(documents)
        result = get_chain(normalized_persona).invoke(
            {"documents": formatted_documents, "question": normalized_question}
        )
    except Exception as error:
        raise RuntimeError(
            "The chat backend is unavailable. Check that Ollama is running and the models are installed."
        ) from error

    sources = list(dict.fromkeys(document.source for document in retrieved_documents))

    return ChatResponse(
        answer=str(result).strip(),
        sources=sources,
        retrieved_documents=retrieved_documents,
    )


def stream_answer_question(
    question: str,
    persona: str = ACCOUNTANT_PERSONA,
) -> tuple[list[RetrievedDocument], Iterator[str]]:
    normalized_persona = _normalize_persona(persona)
    normalized_question, documents, retrieved_documents = _prepare_question(
        question,
        normalized_persona,
    )

    try:
        formatted_documents = format_documents(documents)
        stream = get_chain(normalized_persona).stream(
            {"documents": formatted_documents, "question": normalized_question}
        )
    except Exception as error:
        raise RuntimeError(
            "The chat backend is unavailable. Check that Ollama is running and the models are installed."
        ) from error

    def generate() -> Iterator[str]:
        for chunk in stream:
            yield str(chunk)

    return retrieved_documents, generate()
