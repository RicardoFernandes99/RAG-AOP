from unittest.mock import patch

from langchain_core.documents import Document

from app.services.chat_service import (
    ChatResponse,
    RetrievedDocument,
    answer_question,
    format_documents,
    stream_answer_question,
)


def test_format_documents_includes_source_page_and_content():
    documents = [
        Document(
            page_content="Texto do documento",
            metadata={"source": "Data\\manual.pdf", "page": 3},
        )
    ]

    formatted = format_documents(documents)

    assert "Document: manual.pdf" in formatted
    assert "Page: 3" in formatted
    assert "Content: Texto do documento" in formatted


@patch("app.services.chat_service.get_chain")
@patch("app.services.chat_service.get_retriever")
def test_answer_question_returns_sources_and_context(mock_get_retriever, mock_get_chain):
    mock_get_retriever.return_value.invoke.return_value = [
        Document(
            page_content="Regra contabilistica",
            metadata={"source": "Data\\dl_snc_anexo.pdf", "page": 10},
        )
    ]
    mock_get_chain.return_value.invoke.return_value = "Resposta final"

    response = answer_question("Qual e a regra?")

    assert isinstance(response, ChatResponse)
    assert response.answer == "Resposta final"
    assert response.sources == ["dl_snc_anexo.pdf"]
    assert response.retrieved_documents == [
        RetrievedDocument(
            source="dl_snc_anexo.pdf",
            page=10,
            content="Regra contabilistica",
        )
    ]


def test_answer_question_rejects_empty_input():
    try:
        answer_question("   ")
    except ValueError as error:
        assert str(error) == "Question cannot be empty."
    else:
        raise AssertionError("Expected ValueError for empty question.")


@patch("app.services.chat_service.get_chain")
@patch("app.services.chat_service.get_retriever")
def test_stream_answer_question_returns_documents_and_chunks(
    mock_get_retriever, mock_get_chain
):
    mock_get_retriever.return_value.invoke.return_value = [
        Document(
            page_content="Excerto relevante",
            metadata={"source": "Data\\norma.pdf", "page": 7},
        )
    ]
    mock_get_chain.return_value.stream.return_value = iter(["Resposta ", "final"])

    retrieved_documents, stream = stream_answer_question("Explique a norma")

    assert retrieved_documents == [
        RetrievedDocument(
            source="norma.pdf",
            page=7,
            content="Excerto relevante",
        )
    ]
    assert list(stream) == ["Resposta ", "final"]


@patch("app.services.chat_service.get_retriever")
def test_answer_question_maps_retriever_failure_to_runtime_error(mock_get_retriever):
    mock_get_retriever.return_value.invoke.side_effect = RuntimeError("db offline")

    try:
        answer_question("Qual e a regra?")
    except RuntimeError as error:
        assert str(error) == "The document retriever is unavailable."
    else:
        raise AssertionError("Expected RuntimeError for retriever failure.")


@patch("app.services.chat_service.get_chain")
@patch("app.services.chat_service.get_retriever")
def test_answer_question_maps_generation_failure_to_runtime_error(
    mock_get_retriever, mock_get_chain
):
    mock_get_retriever.return_value.invoke.return_value = [
        Document(page_content="Regra contabilistica", metadata={"source": "Data\\a.pdf"})
    ]
    mock_get_chain.return_value.invoke.side_effect = RuntimeError("ollama offline")

    try:
        answer_question("Qual e a regra?")
    except RuntimeError as error:
        assert (
            str(error)
            == "The chat backend is unavailable. Check that Ollama is running and the models are installed."
        )
    else:
        raise AssertionError("Expected RuntimeError for generation failure.")
