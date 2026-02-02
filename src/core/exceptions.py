"""
Custom exceptions for the PersonX AI Assistant.
"""
from typing import Any


class PersonXException(Exception):
    """Base exception for all PersonX errors."""
    
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class DatabaseError(PersonXException):
    """Database operation failed."""
    pass


class NotFoundError(PersonXException):
    """Resource not found."""
    pass


class ValidationError(PersonXException):
    """Data validation failed."""
    pass


class LLMError(PersonXException):
    """LLM API call failed."""
    pass


class AuthenticationError(PersonXException):
    """Authentication failed."""
    pass


class AuthorizationError(PersonXException):
    """User not authorized for this action."""
    pass


class RateLimitError(PersonXException):
    """Rate limit exceeded."""
    pass


class ConfigurationError(PersonXException):
    """Application configuration error."""
    pass
