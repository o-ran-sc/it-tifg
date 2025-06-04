"""
Error handling module for the Hybrid M-Plane Test Runner.

This module provides a centralized error handling system with custom exceptions
and utilities for consistent error reporting and logging across the codebase.
"""

from .exceptions import (
    HybridMPlaneError,
    ConfigurationError,
    ControllerError,
    TestCaseError,
    SimulatorError,
    NetworkError,
    TimeoutError,
    ValidationError,
)

from .handler import (
    ErrorHandler,
    handle_error,
    log_error,
    with_error_handling,
)

__all__ = [
    # Exceptions
    "HybridMPlaneError",
    "ConfigurationError",
    "ControllerError",
    "TestCaseError",
    "SimulatorError",
    "NetworkError",
    "TimeoutError",
    "ValidationError",
    # Error handling utilities
    "ErrorHandler",
    "handle_error",
    "log_error",
    "with_error_handling",
]