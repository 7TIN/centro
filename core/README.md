# Centro - PersonX AI Assistant

AI personality and assistant built with FastAPI, LangGraph, and LangChain.

## Setup

1. Clone the repository
2. Copy .env.example to .env and fill in your settings (no API keys required)
3. Install dependencies: `uv sync`
4. Run migrations: `uv run alembic upgrade head`
5. Start dev server: `uv run uvicorn src.main:app --reload`

## Project Structure

- src/ - Main application code
- config/ - Configuration and settings
- data/ - Knowledge base and embeddings
- 	ests/ - Test files
- scripts/ - Utility scripts

```
centro
├─ alembic
│  └─ versions
├─ config
│  ├─ prompts.py
│  ├─ settings.py
│  └─ __init__.py
├─ data
│  ├─ embeddings
│  └─ knowledge_base
├─ docker-compose.yml
├─ Dockerfile
├─ pyproject.toml
├─ README.md
├─ scripts
│  ├─ ingest_knowledge.py
│  └─ __init__.py
├─ setup_structure.ps1
├─ src
│  ├─ agents
│  │  ├─ orchestrator.py
│  │  └─ __init__.py
│  ├─ api
│  │  └─ v1
│  │     └─ routes
│  │        ├─ routes.py
│  │        └─ __init__.py
│  ├─ core
│  │  └─ __init__.py
│  ├─ models
│  │  └─ __init__.py
│  └─ services
│     ├─ memory.py
│     ├─ vector_store.py
│     └─ __init__.py
├─ tests
│  ├─ integration
│  │  └─ __init__.py
│  └─ unit
│     └─ __init__.py
└─ uv.lock

```
