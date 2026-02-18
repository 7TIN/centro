# Person X AI Assistant (Core Backend)

FastAPI backend for a personal AI teammate assistant.

## Product Context

Teams often depend on one high-ownership person (Person X) for unblockers and key decisions.
When that person is unavailable, teammates still need accurate context to move work forward.

This backend powers a personal AI assistant that answers on behalf of that person using curated profile and knowledge context.

## What It Handles

- Person profile management
- Person-scoped knowledge management
- Persona-aware chat responses
- Optional retrieval indexing and search

## Tech Stack

- FastAPI
- Pydantic
- Gemini model integration
- Pinecone retrieval (optional)

## Run Locally

```bash
cp .env.example .env
uv sync
uv run python -m uvicorn src.main:app --reload
```

Note: python -m uvicorn is recommended when uv run uvicorn has script-path issues on some Windows setups.

## Repository Layout

- src/ - API routes, services, models
- config/ - settings and prompt config
- scripts/ - utility and evaluation scripts
- tests/ - unit and integration tests
- docs/ - development-phase documentation and implementation references

## Docs

- docs/PLAN.md
- docs/IMPLEMENTATION_GUIDE.md
- docs/README.md
