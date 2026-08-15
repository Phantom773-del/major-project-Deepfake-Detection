# PHANTOM PHOENIX — Backend

Digital Media Authenticity & AI Forensic Intelligence Platform.

Backend: FastAPI + PostgreSQL (SQLAlchemy 2.x + Alembic). Python 3.14 managed with `uv`.

## Development

```bash
docker compose up -d postgres
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

See `docs/BACKEND_IMPLEMENTATION.md` for the engineering record and `docs/API_CONTRACTS.md` for interfaces.
