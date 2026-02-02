"""
Pydantic schemas for API request/response validation.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, EmailStr, field_validator


# ============================================================================
# Health Check Schemas
# ============================================================================

class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Service status")
    environment: str = Field(..., description="Environment (dev/staging/prod)")
    version: str = Field(..., description="API version")
    database: bool = Field(..., description="Database connection status")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# User Schemas
# ============================================================================

class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr
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
    
    class Config:
        from_attributes = True


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
    metadata: Optional[dict]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


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
    metadata: Optional[dict]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


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
    metadata: Optional[dict]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


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
    metadata: Optional[dict]
    created_at: datetime
    
    class Config:
        from_attributes = True


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
# Error Schemas
# ============================================================================

class ErrorResponse(BaseModel):
    """Schema for error responses."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[dict] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
