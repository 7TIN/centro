"""
Main FastAPI application.
"""
from contextlib import asynccontextmanager
import logging
import uuid

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from config.settings import get_settings
from src.core.exceptions import (
    PersonXException,
    NotFoundError,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    RateLimitError,
    ConfigurationError,
)
from src.models.schemas import (
    HealthResponse,
    ErrorResponse,
    ChatRequest,
    ChatResponse,
    RetrievalIndexRequest,
    RetrievalIndexResponse,
    RetrievalSearchRequest,
    RetrievalSearchResponse,
    RetrievedDocument,
)
from src.services.prompt_builder import build_prompt, collect_knowledge_inputs
from src.services.gemini_client import generate_text
from src.services.vector_store import VectorStoreService

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()
_vector_store_service: VectorStoreService | None = None


def get_vector_store_service() -> VectorStoreService:
    """Lazily initialize vector store only when retrieval is requested."""
    global _vector_store_service
    if _vector_store_service is None:
        _vector_store_service = VectorStoreService()
    return _vector_store_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    # Startup
    logger.info(f"Starting {settings.app_name} in {settings.environment} mode")
    
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    logger.info("Application shutdown complete")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="AI proxy for team members - never be blocked by 'Person X is on vacation' again",
    version="0.1.0",
    lifespan=lifespan,
    debug=settings.debug,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.is_development else ["https://yourfrontend.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Exception Handlers
# ============================================================================

@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError):
    """Handle NotFoundError exceptions."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=ErrorResponse(
            error="not_found",
            message=exc.message,
            details=exc.details,
        ).model_dump(mode="json"),
    )


@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    """Handle ValidationError exceptions."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            error="validation_error",
            message=exc.message,
            details=exc.details,
        ).model_dump(mode="json"),
    )


@app.exception_handler(AuthenticationError)
async def authentication_error_handler(request: Request, exc: AuthenticationError):
    """Handle AuthenticationError exceptions."""
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content=ErrorResponse(
            error="authentication_error",
            message=exc.message,
            details=exc.details,
        ).model_dump(mode="json"),
    )


@app.exception_handler(AuthorizationError)
async def authorization_error_handler(request: Request, exc: AuthorizationError):
    """Handle AuthorizationError exceptions."""
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content=ErrorResponse(
            error="authorization_error",
            message=exc.message,
            details=exc.details,
        ).model_dump(mode="json"),
    )


@app.exception_handler(RateLimitError)
async def rate_limit_error_handler(request: Request, exc: RateLimitError):
    """Handle RateLimitError exceptions."""
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content=ErrorResponse(
            error="rate_limit_error",
            message=exc.message,
            details=exc.details,
        ).model_dump(mode="json"),
    )


@app.exception_handler(PersonXException)
async def personx_exception_handler(request: Request, exc: PersonXException):
    """Handle all other PersonX exceptions."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="internal_error",
            message=exc.message,
            details=exc.details,
        ).model_dump(mode="json"),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="internal_error",
            message="An unexpected error occurred",
            details={"error": str(exc)} if settings.debug else {},
        ).model_dump(mode="json"),
    )


# ============================================================================
# Routes
# ============================================================================

@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint."""
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint.
    Returns the status of the application and its dependencies.
    """
    return HealthResponse(
        status="healthy",
        environment=settings.environment,
        version=settings.api_version,
        database=False,
    )


@app.post("/v1/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(request: ChatRequest):
    """
    Simple Gemini-only chat endpoint.
    No database or authentication required.
    """
    retrieved_docs = []
    if request.use_retrieval:
        top_k = request.retrieval_top_k or settings.retrieval_top_k
        try:
            retrieved_docs = get_vector_store_service().search(
                person_id=request.person_id,
                query=request.message,
                top_k=top_k,
                min_score=settings.retrieval_score_threshold,
            )
        except ConfigurationError as exc:
            raise ValidationError(
                message="Retrieval requested but vector store is not configured",
                details={"error": exc.message},
            ) from exc

    prompt = build_prompt(
        user_message=request.message,
        system_prompt=request.system_prompt,
        person_identity=request.person_identity,
        knowledge_text=request.knowledge_text,
        knowledge_files=request.knowledge_files,
        retrieved_context=retrieved_docs,
    )

    response_text = await generate_text(prompt)

    return ChatResponse(
        response=response_text,
        conversation_id=request.conversation_id or str(uuid.uuid4()),
        message_id=str(uuid.uuid4()),
        metadata={
            "model": settings.gemini_model,
            "retrieval_used": request.use_retrieval,
            "retrieved_chunks": len(retrieved_docs),
            "retrieval_sources": [
                doc.get("source")
                for doc in retrieved_docs
                if doc.get("source")
            ],
        },
    )


@app.post("/v1/retrieval/index", response_model=RetrievalIndexResponse, tags=["Retrieval"])
async def retrieval_index(request: RetrievalIndexRequest):
    """
    Index knowledge text/files into Pinecone for a given person.
    """
    documents = collect_knowledge_inputs(
        knowledge_text=request.knowledge_text,
        knowledge_files=request.knowledge_files,
    )

    if not documents:
        raise ValidationError(
            message="No knowledge content available for indexing",
            details={"person_id": request.person_id},
        )

    try:
        indexed_chunks = get_vector_store_service().upsert_documents(
            person_id=request.person_id,
            documents=documents,
            source=request.source,
        )
    except ConfigurationError as exc:
        raise ValidationError(
            message="Retrieval indexing requested but vector store is not configured",
            details={"error": exc.message},
        ) from exc

    return RetrievalIndexResponse(
        person_id=request.person_id,
        indexed_chunks=indexed_chunks,
        source=request.source,
    )


@app.post("/v1/retrieval/search", response_model=RetrievalSearchResponse, tags=["Retrieval"])
async def retrieval_search(request: RetrievalSearchRequest):
    """
    Search person-scoped knowledge from Pinecone.
    """
    try:
        matches = get_vector_store_service().search(
            person_id=request.person_id,
            query=request.query,
            top_k=request.top_k,
            min_score=request.min_score,
        )
    except ConfigurationError as exc:
        raise ValidationError(
            message="Retrieval search requested but vector store is not configured",
            details={"error": exc.message},
        ) from exc

    results = [
        RetrievedDocument(
            id=match.get("id", ""),
            score=float(match.get("score", 0.0)),
            source=match.get("source"),
            content=match.get("text", ""),
            metadata=match.get("metadata", {}),
        )
        for match in matches
    ]

    return RetrievalSearchResponse(
        person_id=request.person_id,
        query=request.query,
        results=results,
    )


# ============================================================================
# API Router Registration (will add in next steps)
# ============================================================================

# from src.api.v1.routes.person import router as person_router
# from src.api.v1.routes.knowledge import router as knowledge_router
# from src.api.v1.routes.chat import router as chat_router

# app.include_router(person_router, prefix=f"/{settings.api_version}")
# app.include_router(knowledge_router, prefix=f"/{settings.api_version}")
# app.include_router(chat_router, prefix=f"/{settings.api_version}")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.is_development,
        log_level=settings.log_level.lower(),
    )
