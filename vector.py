from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

PDF_DIRECTORY = Path("Data")
DB_LOCATION = Path("chroma_langchain_db")
EMBED_MODEL = "mxbai-embed-large"


def load_pdf_documents(pdf_directory: Path) -> list[Document]:
    documents: list[Document] = []

    for pdf_path in sorted(pdf_directory.rglob("*.pdf")):
        reader = PdfReader(str(pdf_path))
        for page_number, page in enumerate(reader.pages, start=1):
            page_text = (page.extract_text() or "").strip()
            if not page_text:
                continue

            documents.append(
                Document(
                    page_content=page_text,
                    metadata={
                        "source": str(pdf_path),
                        "page": page_number,
                    },
                )
            )

    return documents


def build_vector_store() -> Chroma:
    embeddings = OllamaEmbeddings(model=EMBED_MODEL)
    vector_store = Chroma(
        collection_name="pdf_collection",
        embedding_function=embeddings,
        persist_directory=str(DB_LOCATION),
    )

    collection_count = vector_store._collection.count()
    if DB_LOCATION.exists() and collection_count > 0:
        return vector_store

    if not PDF_DIRECTORY.exists():
        raise FileNotFoundError(
            f"PDF directory not found: {PDF_DIRECTORY.resolve()}. "
            "Create it and add your PDF files first."
        )

    documents = load_pdf_documents(PDF_DIRECTORY)
    if not documents:
        raise ValueError(f"No readable PDF content found in {PDF_DIRECTORY.resolve()}.")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
    )
    chunks = splitter.split_documents(documents)
    ids = [f"doc-{index}" for index in range(len(chunks))]

    if collection_count > 0:
        vector_store.delete(ids=vector_store.get()["ids"])

    vector_store.add_documents(documents=chunks, ids=ids)
    return vector_store


vector_store = build_vector_store()
retriever = vector_store.as_retriever(search_kwargs={"k": 8})
