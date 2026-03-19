import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

PDF_DIRECTORY = Path(os.getenv("PDF_DIRECTORY", str(BASE_DIR / "Data")))
CHROMA_DB_LOCATION = Path(
    os.getenv("CHROMA_DB_LOCATION", str(BASE_DIR / "chroma_langchain_db"))
)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_CHAT_MODEL = os.getenv("OLLAMA_CHAT_MODEL", "llama3.2")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "mxbai-embed-large")

POSTGRES_DB = os.getenv("POSTGRES_DB", "rag_aop")
POSTGRES_USER = os.getenv("POSTGRES_USER", "rag_aop")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "rag_aop")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}",
)

SQLITE_DB_PATH = Path(os.getenv("SQLITE_DB_PATH", str(BASE_DIR / "app_data.sqlite3")))
SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "rag_aop_session")
SESSION_MAX_AGE_SECONDS = int(os.getenv("SESSION_MAX_AGE_SECONDS", str(60 * 60 * 24 * 30)))
