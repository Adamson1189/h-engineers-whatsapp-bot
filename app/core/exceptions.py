"""
core/exceptions.py

WHY THIS FILE EXISTS:
As this app grows (Phases 4-13), you'll have dozens of places that can fail:
a customer not found, a duplicate registration, a bad OTP, a failed payment.

Instead of scattering raw `raise Exception("...")` everywhere (which gives
messy, inconsistent error responses), we define OUR OWN exception types here.
Every part of the app raises these instead, and FastAPI catches them in ONE
place (see main.py) and turns them into clean, consistent JSON error
responses with the right HTTP status code.

This is the "separate business logic from error formatting" principle.
"""


class AppException(Exception):
    """Base class for all custom exceptions in this app."""

    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NotFoundException(AppException):
    """Raised when a requested resource (customer, ticket, etc.) doesn't exist."""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)


class ValidationException(AppException):
    """Raised when input data fails a business rule (not a pydantic schema rule)."""

    def __init__(self, message: str = "Invalid input"):
        super().__init__(message, status_code=422)


class DuplicateException(AppException):
    """Raised when trying to create something that already exists (e.g. phone number)."""

    def __init__(self, message: str = "Resource already exists"):
        super().__init__(message, status_code=409)


class UnauthorizedException(AppException):
    """Raised for failed login, invalid OTP, or expired/invalid JWT."""

    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, status_code=401)


class ExternalServiceException(AppException):
    """Raised when a call to WhatsApp, Paystack, or OpenAI fails."""

    def __init__(self, message: str = "External service error"):
        super().__init__(message, status_code=502)
