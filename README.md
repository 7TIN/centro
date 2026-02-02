# Centro - PersonX AI Assistant

AI personality and assistant built with FastAPI, LangGraph, and LangChain.

## Setup

1. Clone the repository
2. Copy .env.example to .env and fill in your API keys
3. Install dependencies: `uv sync`
4. Run migrations: `uv run alembic upgrade head`
5. Start dev server: `uv run uvicorn src.main:app --reload`

## Project Structure

- src/ - Main application code
- config/ - Configuration and settings
- data/ - Knowledge base and embeddings
- 	ests/ - Test files
- scripts/ - Utility scripts
