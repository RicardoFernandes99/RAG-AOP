from fastapi import APIRouter

from app.core.config import OLLAMA_CHAT_MODEL, OLLAMA_EMBED_MODEL

router = APIRouter(prefix="/api/models", tags=["models"])


@router.get("")
def get_model_settings() -> dict[str, str]:
    return {
        "chat_model": OLLAMA_CHAT_MODEL,
        "embedding_model": OLLAMA_EMBED_MODEL,
    }
