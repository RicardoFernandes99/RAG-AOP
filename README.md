# RAG-AOP

## Docker

The stack includes:

- `app`: FastAPI RAG API on port `8000`
- `postgres`: PostgreSQL in Docker, exposed on host port `5433`

### Run

1. Copy `.env.example` to `.env` and adjust values if needed.
2. Make sure Ollama is running on the host and the required models are installed.
3. Start the stack:

```bash
docker compose up --build
```

The API will be available at `http://localhost:8000` and PostgreSQL at `localhost:5433`.

For local development without Docker, run:

```bash
uvicorn app.main:app --reload
```

### Notes

- The app reaches Ollama through `OLLAMA_BASE_URL`. The default is `http://host.docker.internal:11434`.
- PDF input is mounted from `./Data`.
- Chroma persistence is stored in the named Docker volume `chroma_data`.
- PostgreSQL persistence is stored in the named Docker volume `postgres_data`.
