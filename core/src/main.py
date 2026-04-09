"""
Main FastAPI application.
"""
from contextlib import asynccontextmanager
import logging

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
    PersonCreate,
    PersonResponse,
    PersonUpdate,
    KnowledgeEntryCreate,
    KnowledgeEntryUpdate,
    KnowledgeEntryResponse,
    RetrievalIndexRequest,
    RetrievalIndexResponse,
    RetrievalSearchRequest,
    RetrievalSearchResponse,
    RetrievedDocument,
    RetrievalSourceDeleteRequest,
    RetrievalSourceReplaceRequest,
    RetrievalSourceActionResponse,
    WikiOverviewResponse,
    WikiPageResponse,
    WikiRebuildResponse,
    TeamWikiOverviewResponse,
    TeamWikiPageResponse,
    TeamKnowledgeUpsertRequest,
    TeamKnowledgeUpsertResponse,
    DemoBootstrapResponse,
)
from src.services.prompt_builder import (
    build_prompt,
    collect_knowledge_inputs,
    build_persona_system_prompt,
)
from src.services.llm_service import generate_with_retry
from src.services.vector_store import VectorStoreService
from src.services.person_service import (
    create_person,
    list_persons,
    get_person,
    update_person,
    try_get_person,
    build_person_identity,
)
from src.services.knowledge_service import (
    add_knowledge_entry,
    list_knowledge_entries,
    update_knowledge_entry,
)
from src.services.conversation_service import ensure_conversation, add_message
from src.services.demo_seed_service import ensure_demo_seed_data
from src.services.wiki_service import (
    get_person_wiki_overview,
    read_person_wiki_page,
    rebuild_person_wiki,
    get_team_wiki_overview,
    read_team_wiki_page,
    upsert_team_knowledge_page,
    render_team_context,
    render_person_context,
    sync_team_snapshot_for_person,
)

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


@app.post("/v1/persons", response_model=PersonResponse, tags=["Persons"])
async def create_person_endpoint(request: PersonCreate):
    """Create a person profile used by MVP persona chat."""
    return create_person(request)


@app.get("/v1/persons", response_model=list[PersonResponse], tags=["Persons"])
async def list_persons_endpoint():
    """List person profiles."""
    return list_persons()


@app.get("/v1/persons/{person_id}", response_model=PersonResponse, tags=["Persons"])
async def get_person_endpoint(person_id: str):
    """Get a person profile."""
    return get_person(person_id)


@app.patch("/v1/persons/{person_id}", response_model=PersonResponse, tags=["Persons"])
async def update_person_endpoint(person_id: str, request: PersonUpdate):
    """Update a person profile."""
    return update_person(person_id, request)


@app.post(
    "/v1/persons/{person_id}/knowledge",
    response_model=KnowledgeEntryResponse,
    tags=["Knowledge"],
)
async def add_knowledge_endpoint(person_id: str, request: KnowledgeEntryCreate):
    """Add knowledge entry for a person profile."""
    return add_knowledge_entry(person_id, request)


@app.get(
    "/v1/persons/{person_id}/knowledge",
    response_model=list[KnowledgeEntryResponse],
    tags=["Knowledge"],
)
async def list_knowledge_endpoint(person_id: str):
    """List knowledge entries for a person profile."""
    return list_knowledge_entries(person_id)


@app.patch(
    "/v1/persons/{person_id}/knowledge/{knowledge_id}",
    response_model=KnowledgeEntryResponse,
    tags=["Knowledge"],
)
async def update_knowledge_endpoint(
    person_id: str,
    knowledge_id: str,
    request: KnowledgeEntryUpdate,
):
    """Update knowledge entry for a person profile."""
    return update_knowledge_entry(person_id=person_id, knowledge_id=knowledge_id, payload=request)


@app.get(
    "/v1/persons/{person_id}/wiki",
    response_model=WikiOverviewResponse,
    tags=["Wiki"],
)
async def get_person_wiki_endpoint(person_id: str):
    """Get index, log, and page summaries for a person's persistent wiki."""
    get_person(person_id)
    return WikiOverviewResponse(**get_person_wiki_overview(person_id))


@app.get(
    "/v1/persons/{person_id}/wiki/pages/{page_path:path}",
    response_model=WikiPageResponse,
    tags=["Wiki"],
)
async def read_person_wiki_page_endpoint(person_id: str, page_path: str):
    """Read an individual markdown page from the person's wiki."""
    get_person(person_id)
    return WikiPageResponse(**read_person_wiki_page(person_id=person_id, page_path=page_path))


@app.post(
    "/v1/persons/{person_id}/wiki/rebuild",
    response_model=WikiRebuildResponse,
    tags=["Wiki"],
)
async def rebuild_person_wiki_endpoint(person_id: str):
    """Rebuild a person's wiki from current profile + knowledge entries."""
    person = get_person(person_id)
    entries = list_knowledge_entries(person_id)
    stats = rebuild_person_wiki(person=person, knowledge_entries=entries)
    return WikiRebuildResponse(person_id=person_id, **stats)


@app.get("/v1/team/wiki", response_model=TeamWikiOverviewResponse, tags=["Wiki"])
async def get_team_wiki_endpoint():
    """Get overview for the shared core team wiki."""
    return TeamWikiOverviewResponse(**get_team_wiki_overview())


@app.get(
    "/v1/team/wiki/pages/{page_path:path}",
    response_model=TeamWikiPageResponse,
    tags=["Wiki"],
)
async def read_team_wiki_page_endpoint(page_path: str):
    """Read an individual markdown page from shared team wiki."""
    return TeamWikiPageResponse(**read_team_wiki_page(page_path))


@app.post(
    "/v1/team/wiki/knowledge",
    response_model=TeamKnowledgeUpsertResponse,
    tags=["Wiki"],
)
async def upsert_team_knowledge_endpoint(request: TeamKnowledgeUpsertRequest):
    """Upsert team knowledge and sync team snapshot into all person wikis."""
    payload = upsert_team_knowledge_page(
        title=request.title,
        content=request.content,
        page_slug=request.page_slug,
        source_reference=request.source_reference,
        tags=request.tags,
        updated_by=request.updated_by,
        sync_person_wikis=True,
    )
    return TeamKnowledgeUpsertResponse(**payload)


@app.post("/v1/demo/bootstrap", response_model=DemoBootstrapResponse, tags=["Demo"])
async def demo_bootstrap_endpoint():
    """Seed server-side demo team/person markdown data and return selector payload."""
    payload = ensure_demo_seed_data()
    return DemoBootstrapResponse(**payload)


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
                enable_hybrid_fallback=True,
            )
        except ConfigurationError as exc:
            raise ValidationError(
                message="Retrieval requested but vector store is not configured",
                details={"error": exc.message},
            ) from exc

    person = try_get_person(request.person_id)
    resolved_system_prompt = request.system_prompt
    resolved_person_identity = request.person_identity

    team_wiki_context = ""
    person_wiki_context = ""
    knowledge_count = 0
    if person:
        if not resolved_system_prompt:
            resolved_system_prompt = build_persona_system_prompt(
                base_prompt=person.base_system_prompt,
                name=person.name,
                role=person.role,
                team=person.department,
                communication_style=person.communication_style,
            )
        if not resolved_person_identity:
            resolved_person_identity = build_person_identity(person)

        person_knowledge = list_knowledge_entries(request.person_id)
        knowledge_count = len(person_knowledge)
        # Keep personal wiki synced with latest team wiki snapshot before prompt build.
        sync_team_snapshot_for_person(request.person_id)
        team_wiki_context = render_team_context(
            max_pages=settings.wiki_context_max_pages,
            max_chars=settings.wiki_context_max_chars,
        )
        person_wiki_context = render_person_context(
            person_id=request.person_id,
            max_pages=settings.wiki_context_max_pages,
            max_chars=settings.wiki_context_max_chars,
        )

    inline_knowledge_inputs = collect_knowledge_inputs(
        knowledge_text=request.knowledge_text,
        knowledge_files=request.knowledge_files,
    )
    if person_wiki_context:
        inline_knowledge_inputs.insert(0, person_wiki_context)
    if team_wiki_context:
        inline_knowledge_inputs.insert(0, team_wiki_context)
    merged_knowledge_text = "\n\n".join(inline_knowledge_inputs).strip() if inline_knowledge_inputs else None

    prompt = build_prompt(
        user_message=request.message,
        system_prompt=resolved_system_prompt,
        person_identity=resolved_person_identity,
        knowledge_text=merged_knowledge_text,
        knowledge_files=None,
        retrieved_context=retrieved_docs,
    )

    response_text = await generate_with_retry(prompt)

    conversation = ensure_conversation(
        person_id=request.person_id,
        conversation_id=request.conversation_id,
    )
    add_message(
        conversation_id=conversation.id,
        role="user",
        content=request.message,
    )
    assistant_message = add_message(
        conversation_id=conversation.id,
        role="assistant",
        content=response_text,
        model=settings.gemini_model,
        metadata={
            "retrieval_used": request.use_retrieval,
            "retrieved_chunks": len(retrieved_docs),
            "person_found": person is not None,
            "knowledge_entries_used": knowledge_count,
            "team_context_used": bool(team_wiki_context),
            "person_wiki_context_used": bool(person_wiki_context),
        },
    )

    return ChatResponse(
        response=response_text,
        conversation_id=conversation.id,
        message_id=assistant_message.id,
        metadata={
            "model": settings.gemini_model,
            "retrieval_used": request.use_retrieval,
            "retrieved_chunks": len(retrieved_docs),
            "retrieval_sources": [
                doc.get("source")
                for doc in retrieved_docs
                if doc.get("source")
            ],
            "person_found": person is not None,
            "knowledge_entries_used": knowledge_count,
            "team_context_used": bool(team_wiki_context),
            "person_wiki_context_used": bool(person_wiki_context),
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
            enable_hybrid_fallback=True,
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
            retrieval_mode=match.get("retrieval_mode"),
            metadata=match.get("metadata", {}),
        )
        for match in matches
    ]

    return RetrievalSearchResponse(
        person_id=request.person_id,
        query=request.query,
        results=results,
    )


@app.post(
    "/v1/retrieval/source/delete",
    response_model=RetrievalSourceActionResponse,
    tags=["Retrieval"],
)
async def retrieval_delete_source(request: RetrievalSourceDeleteRequest):
    """
    Delete all indexed chunks for a person/source pair.
    """
    try:
        deleted = get_vector_store_service().delete_by_source(
            person_id=request.person_id,
            source=request.source,
        )
    except ConfigurationError as exc:
        raise ValidationError(
            message="Retrieval delete requested but vector store is not configured",
            details={"error": exc.message},
        ) from exc

    return RetrievalSourceActionResponse(
        person_id=request.person_id,
        source=request.source,
        deleted_chunks=deleted,
        indexed_chunks=0,
    )


@app.post(
    "/v1/retrieval/source/replace",
    response_model=RetrievalSourceActionResponse,
    tags=["Retrieval"],
)
async def retrieval_replace_source(request: RetrievalSourceReplaceRequest):
    """
    Replace all indexed chunks for a person/source pair.
    """
    documents = collect_knowledge_inputs(
        knowledge_text=request.knowledge_text,
        knowledge_files=request.knowledge_files,
    )

    try:
        deleted, indexed = get_vector_store_service().replace_source_documents(
            person_id=request.person_id,
            source=request.source,
            documents=documents,
        )
    except ConfigurationError as exc:
        raise ValidationError(
            message="Retrieval replace requested but vector store is not configured",
            details={"error": exc.message},
        ) from exc

    return RetrievalSourceActionResponse(
        person_id=request.person_id,
        source=request.source,
        deleted_chunks=deleted,
        indexed_chunks=indexed,
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
