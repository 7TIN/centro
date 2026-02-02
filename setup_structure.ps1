# Create main directories
$dirs = @(
    "config",
    "src/agents",
    "src/models",
    "src/services",
    "src/api/v1/routes",
    "src/core",
    "data/knowledge_base",
    "data/embeddings",
    "data/logs",
    "tests/unit",
    "tests/integration",
    "scripts",
    "alembic/versions"
)

foreach ($dir in $dirs) {
    New-Item -ItemType Directory -Force -Path $dir
    # Create __init__.py for Python packages
    if ($dir -like "src/*" -or $dir -like "tests/*" -or $dir -like "config" -or $dir -like "scripts") {
        New-Item -ItemType File -Force -Path "$dir/__init__.py"
    }
}

# Create essential files
$files = @{
    ".env.example" = @"
# App
DEBUG=false
APP_NAME=PersonX Assistant

# API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
PINECONE_API_KEY=...

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/centro
REDIS_URL=redis://localhost:6379

# Pinecone
PINECONE_ENVIRONMENT=us-east-1
PINECONE_INDEX_NAME=personx-knowledge
"@

    ".gitignore" = @"
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
.venv/
venv/

# Environment
.env
.env.local

# IDEs
.vscode/
.idea/
*.swp
*.swo

# Testing
.pytest_cache/
.coverage
htmlcov/
.mypy_cache/
.ruff_cache/

# Data
data/logs/
*.db
*.sqlite

# OS
.DS_Store
Thumbs.db

# Build
dist/
build/
*.egg-info/
"@

    "README.md" = @"
# Centro - PersonX AI Assistant

AI personality and assistant built with FastAPI, LangGraph, and LangChain.

## Setup

1. Clone the repository
2. Copy `.env.example` to `.env` and fill in your API keys
3. Install dependencies: ``uv sync``
4. Run migrations: ``uv run alembic upgrade head``
5. Start dev server: ``uv run uvicorn src.main:app --reload``

## Project Structure

- `src/` - Main application code
- `config/` - Configuration and settings
- `data/` - Knowledge base and embeddings
- `tests/` - Test files
- `scripts/` - Utility scripts
"@

    "docker-compose.yml" = @"
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: centro
      POSTGRES_PASSWORD: centro
      POSTGRES_DB: centro
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
"@

    "Dockerfile" = @"
FROM python:3.11-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy application
COPY . .

# Run the application
CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
"@
}

foreach ($file in $files.Keys) {
    Set-Content -Path $file -Value $files[$file]
}

Write-Host "✅ Project structure created successfully!" -ForegroundColor Green
Write-Host "`nNext steps:" -ForegroundColor Yellow
Write-Host "1. Copy .env.example to .env and fill in your API keys"
Write-Host "2. Run: uv sync"
Write-Host "3. Create your application files in src/"