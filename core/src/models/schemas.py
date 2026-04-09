"""
Pydantic schemas for API request/response validation.
"""
from datetime import datetime, timezone
from typing import Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator, model_validator


def utc_now() -> datetime:
    """Return timezone-aware UTC timestamp for schema defaults."""
    return datetime.now(timezone.utc)


# ============================================================================
# Health Check Schemas
# ============================================================================

class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Service status")
    environment: str = Field(..., description="Environment (dev/staging/prod)")
    version: str = Field(..., description="API version")
    database: bool = Field(..., description="Database connection status")
    timestamp: datetime = Field(default_factory=utc_now)


# ============================================================================
# User Schemas
# ============================================================================

class UserBase(BaseModel):
    """Base user schema."""
    email: str = Field(..., max_length=255)
    username: str = Field(..., min_length=3, max_length=100)
    full_name: Optional[str] = Field(None, max_length=255)


class UserCreate(UserBase):
    """Schema for creating a user."""
    password: str = Field(..., min_length=8)


class UserResponse(UserBase):
    """Schema for user response."""
    id: str
    is_active: bool
    is_admin: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Person Schemas
# ============================================================================

class PersonBase(BaseModel):
    """Base person schema."""
    name: str = Field(..., min_length=1, max_length=255)
    role: Optional[str] = Field(None, max_length=255)
    department: Optional[str] = Field(None, max_length=255)


class PersonCreate(PersonBase):
    """Schema for creating a person."""
    base_system_prompt: Optional[str] = Field(
        None,
        description="Base system prompt template for this person's AI"
    )
    communication_style: Optional[dict] = Field(
        None,
        description="Communication style preferences (tone, formality, etc.)"
    )
    metadata: Optional[dict] = Field(None, description="Additional metadata")


class PersonUpdate(BaseModel):
    """Schema for updating a person."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    role: Optional[str] = Field(None, max_length=255)
    department: Optional[str] = Field(None, max_length=255)
    base_system_prompt: Optional[str] = None
    communication_style: Optional[dict] = None
    is_active: Optional[bool] = None
    metadata: Optional[dict] = None


class PersonResponse(PersonBase):
    """Schema for person response."""
    id: str
    base_system_prompt: Optional[str]
    communication_style: Optional[dict]
    is_active: bool
    metadata: Optional[dict] = Field(
        default=None,
        validation_alias=AliasChoices("metadata", "profile_metadata"),
    )
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Knowledge Entry Schemas
# ============================================================================

class KnowledgeEntryBase(BaseModel):
    """Base knowledge entry schema."""
    content: str = Field(..., min_length=1)
    title: Optional[str] = Field(None, max_length=500)
    summary: Optional[str] = None
    source_type: str = Field(
        ...,
        description="Source type: manual, document, meeting, slack, email, git_pr, etc."
    )
    source_reference: Optional[str] = Field(
        None,
        max_length=500,
        description="Reference to source (file path, URL, etc.)"
    )
    tags: Optional[list[str]] = Field(None, description="Tags for categorization")
    priority: int = Field(5, ge=1, le=10, description="Priority level (1-10)")


class KnowledgeEntryCreate(KnowledgeEntryBase):
    """Schema for creating a knowledge entry."""
    metadata: Optional[dict] = Field(None, description="Additional metadata")


class KnowledgeEntryUpdate(BaseModel):
    """Schema for updating a knowledge entry."""
    content: Optional[str] = Field(None, min_length=1)
    title: Optional[str] = Field(None, max_length=500)
    summary: Optional[str] = None
    source_type: Optional[str] = None
    source_reference: Optional[str] = Field(None, max_length=500)
    tags: Optional[list[str]] = None
    priority: Optional[int] = Field(None, ge=1, le=10)
    metadata: Optional[dict] = None


class KnowledgeEntryResponse(KnowledgeEntryBase):
    """Schema for knowledge entry response."""
    id: str
    person_id: str
    metadata: Optional[dict] = Field(
        default=None,
        validation_alias=AliasChoices("metadata", "entry_metadata"),
    )
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Conversation Schemas
# ============================================================================

class ConversationBase(BaseModel):
    """Base conversation schema."""
    title: Optional[str] = Field(None, max_length=500)


class ConversationCreate(ConversationBase):
    """Schema for creating a conversation."""
    person_id: str = Field(..., description="ID of the person to chat with")


class ConversationResponse(ConversationBase):
    """Schema for conversation response."""
    id: str
    user_id: str
    person_id: str
    is_active: bool
    summary: Optional[str]
    metadata: Optional[dict] = Field(
        default=None,
        validation_alias=AliasChoices("metadata", "context_metadata"),
    )
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Message Schemas
# ============================================================================

class MessageBase(BaseModel):
    """Base message schema."""
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str = Field(..., min_length=1)


class MessageCreate(MessageBase):
    """Schema for creating a message."""
    pass


class MessageResponse(MessageBase):
    """Schema for message response."""
    id: str
    conversation_id: str
    model: Optional[str]
    tokens_used: Optional[int]
    confidence_score: Optional[float]
    metadata: Optional[dict] = Field(
        default=None,
        validation_alias=AliasChoices("metadata", "message_metadata"),
    )
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Chat Schemas (For Step 5)
# ============================================================================

class ChatRequest(BaseModel):
    """Schema for chat request."""
    person_id: str = Field(..., description="ID of the person to chat with")
    message: str = Field(..., min_length=1, description="User's message")
    conversation_id: Optional[str] = Field(
        None,
        description="Existing conversation ID (create new if not provided)"
    )
    system_prompt: Optional[str] = Field(
        None,
        description="Optional system prompt override"
    )
    person_identity: Optional[str] = Field(
        None,
        description="Optional person identity prompt"
    )
    knowledge_text: Optional[str] = Field(
        None,
        description="Optional knowledge context as raw text"
    )
    knowledge_files: Optional[list[str]] = Field(
        None,
        description="Optional list of local file paths to include as knowledge"
    )
    use_retrieval: bool = Field(
        False,
        description="Whether to use Pinecone retrieval for this chat request"
    )
    retrieval_top_k: Optional[int] = Field(
        None,
        ge=1,
        le=20,
        description="Optional top-k override for retrieval results"
    )
    
    @field_validator("message")
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        """Ensure message is not just whitespace."""
        if not v.strip():
            raise ValueError("Message cannot be empty or whitespace only")
        return v.strip()


class ChatResponse(BaseModel):
    """Schema for chat response."""
    response: str = Field(..., description="AI assistant's response")
    conversation_id: str = Field(..., description="Conversation ID")
    message_id: str = Field(..., description="ID of the assistant's message")
    metadata: dict = Field(
        default_factory=dict,
        description="Metadata (model used, confidence, etc.)"
    )


# ============================================================================
# Retrieval Schemas
# ============================================================================

class RetrievalIndexRequest(BaseModel):
    """Schema for indexing knowledge into the vector store."""
    person_id: str = Field(..., description="ID of the person to index knowledge for")
    source: str = Field("manual", description="Source label for indexed content")
    knowledge_text: Optional[str] = Field(
        None,
        description="Optional inline knowledge text to index"
    )
    knowledge_files: Optional[list[str]] = Field(
        None,
        description="Optional list of local files to index"
    )

    @model_validator(mode="after")
    def validate_content_present(self):
        if not (self.knowledge_text and self.knowledge_text.strip()) and not self.knowledge_files:
            raise ValueError("Provide knowledge_text or knowledge_files for indexing")
        return self


class RetrievalIndexResponse(BaseModel):
    """Schema for retrieval indexing response."""
    person_id: str = Field(..., description="Person ID")
    indexed_chunks: int = Field(..., description="Number of chunks indexed")
    source: str = Field(..., description="Source label used for indexing")


class RetrievalSearchRequest(BaseModel):
    """Schema for retrieval search requests."""
    person_id: str = Field(..., description="ID of the person to search for")
    query: str = Field(..., min_length=1, description="Search query")
    top_k: int = Field(5, ge=1, le=20, description="Maximum number of matches")
    min_score: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score threshold"
    )


class RetrievedDocument(BaseModel):
    """Schema for an individual retrieval match."""
    id: str = Field(..., description="Vector ID")
    score: float = Field(..., description="Similarity score")
    source: Optional[str] = Field(None, description="Source label")
    content: str = Field(..., description="Matched text content")
    retrieval_mode: Optional[str] = Field(
        None,
        description="Retrieval mode used: vector or keyword_fallback",
    )
    metadata: dict = Field(default_factory=dict, description="Additional metadata")


class RetrievalSearchResponse(BaseModel):
    """Schema for retrieval search responses."""
    person_id: str = Field(..., description="Person ID")
    query: str = Field(..., description="Search query")
    results: list[RetrievedDocument] = Field(default_factory=list)


class RetrievalSourceDeleteRequest(BaseModel):
    """Delete all indexed chunks for a person/source pair."""
    person_id: str = Field(..., description="Person ID")
    source: str = Field(..., min_length=1, description="Source label")


class RetrievalSourceReplaceRequest(BaseModel):
    """Replace all chunks for a person/source pair."""
    person_id: str = Field(..., description="Person ID")
    source: str = Field(..., min_length=1, description="Source label")
    knowledge_text: Optional[str] = Field(
        None,
        description="Inline knowledge to index",
    )
    knowledge_files: Optional[list[str]] = Field(
        None,
        description="Local files to index",
    )

    @model_validator(mode="after")
    def validate_content_present(self):
        if not (self.knowledge_text and self.knowledge_text.strip()) and not self.knowledge_files:
            raise ValueError("Provide knowledge_text or knowledge_files for source replacement")
        return self


class RetrievalSourceActionResponse(BaseModel):
    """Response for source delete/replace actions."""
    person_id: str = Field(..., description="Person ID")
    source: str = Field(..., description="Source label")
    deleted_chunks: int = Field(..., description="Deleted chunk count")
    indexed_chunks: int = Field(0, description="Indexed chunk count for replace operations")


# ============================================================================
# Wiki Schemas
# ============================================================================

class WikiPageSummary(BaseModel):
    """Summary metadata for a wiki page."""
    path: str = Field(..., description="Relative page path in the person's wiki")
    title: str = Field(..., description="Page title")
    updated_at: str = Field(..., description="Last modified time (ISO-8601)")


class WikiOverviewResponse(BaseModel):
    """Overview response for a person's wiki."""
    person_id: str = Field(..., description="Person ID")
    root_path: str = Field(..., description="Absolute filesystem path for this person's wiki")
    index_content: str = Field("", description="Contents of index.md")
    log_content: str = Field("", description="Contents of log.md")
    pages: list[WikiPageSummary] = Field(default_factory=list)


class WikiPageResponse(BaseModel):
    """Read response for an individual wiki page."""
    person_id: str = Field(..., description="Person ID")
    path: str = Field(..., description="Relative wiki page path")
    title: str = Field(..., description="Page title")
    updated_at: str = Field(..., description="Last modified time (ISO-8601)")
    content: str = Field(..., description="Markdown page content")


class WikiRebuildResponse(BaseModel):
    """Response for wiki rebuild operations."""
    person_id: str = Field(..., description="Person ID")
    written_pages: int = Field(..., ge=0, description="Knowledge pages written")
    removed_pages: int = Field(..., ge=0, description="Stale pages removed")


class TeamWikiOverviewResponse(BaseModel):
    """Overview response for the core team wiki."""
    team_id: str = Field(..., description="Team wiki ID")
    team_name: str = Field(..., description="Team wiki display name")
    root_path: str = Field(..., description="Absolute filesystem path for the team wiki")
    index_content: str = Field("", description="Contents of team index page")
    log_content: str = Field("", description="Contents of team log page")
    pages: list[WikiPageSummary] = Field(default_factory=list)


class TeamWikiPageResponse(BaseModel):
    """Read response for an individual team wiki page."""
    team_id: str = Field(..., description="Team wiki ID")
    path: str = Field(..., description="Relative page path")
    title: str = Field(..., description="Page title")
    updated_at: str = Field(..., description="Last modified time (ISO-8601)")
    content: str = Field(..., description="Markdown page content")


class TeamKnowledgeUpsertRequest(BaseModel):
    """Request to add/update a knowledge page in shared team wiki."""
    title: str = Field(..., min_length=1, max_length=300)
    content: str = Field(..., min_length=1)
    page_slug: Optional[str] = Field(None, max_length=300)
    source_reference: Optional[str] = Field(None, max_length=500)
    tags: Optional[list[str]] = None
    updated_by: Optional[str] = Field(None, max_length=255)


class TeamKnowledgeUpsertResponse(BaseModel):
    """Response after writing shared team knowledge page."""
    team_id: str
    page_path: str
    updated_at: str
    synced_person_wikis: int = Field(..., ge=0)


class DemoPersonSummary(BaseModel):
    """Demo person descriptor returned to frontend selector."""
    id: str
    name: str
    role: Optional[str] = None
    department: Optional[str] = None
    first_question: Optional[str] = None
    suggested_questions: list[str] = Field(default_factory=list)


class DemoBootstrapResponse(BaseModel):
    """Bootstrap response for server-side demo seed data."""
    team_id: str
    team_name: str
    team_pages: int = Field(..., ge=0)
    synced_person_wikis: int = Field(..., ge=0)
    persons: list[DemoPersonSummary] = Field(default_factory=list)
    default_person_id: Optional[str] = None


# ============================================================================
# Ingestion Schemas
# ============================================================================

class GitHubIngestRequest(BaseModel):
    """Request payload for GitHub repository ingestion."""
    owner: str = Field(..., min_length=1, max_length=200)
    repo: str = Field(..., min_length=1, max_length=300)
    person_id: Optional[str] = Field(
        None,
        description="Optional target person to receive a person-level summary entry",
    )
    max_items: int = Field(10, ge=1, le=50)
    include_open_prs: bool = True
    include_open_issues: bool = True
    include_recent_merged_prs: bool = True
    attach_to_person: bool = True
    team_page_slug: Optional[str] = Field(None, max_length=300)
    updated_by: Optional[str] = Field(None, max_length=255)


class GitHubIngestCounts(BaseModel):
    """Counts extracted from ingested repository snapshot."""
    open_prs: int = Field(0, ge=0)
    open_issues: int = Field(0, ge=0)
    merged_prs: int = Field(0, ge=0)


class GitHubIngestResponse(BaseModel):
    """Response after ingesting GitHub data into wiki context."""
    repository: str
    source_url: str
    fetched_at: str
    counts: GitHubIngestCounts
    team_page_path: str
    synced_person_wikis: int = Field(..., ge=0)
    person_id: Optional[str] = None
    person_knowledge_id: Optional[str] = None


# ============================================================================
# Error Schemas
# ============================================================================

class ErrorResponse(BaseModel):
    """Schema for error responses."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[dict] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=utc_now)
