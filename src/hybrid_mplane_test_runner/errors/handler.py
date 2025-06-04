# Copyright 2025 highstreet technologies USA Corp.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Error handling utilities for the Hybrid M-Plane Test Runner.

This module provides functions and classes for consistent error handling
and logging across the codebase.
"""

import functools
import inspect
import logging
import sys
import traceback
from typing import Any, Callable, Dict, Optional, Type, TypeVar, Union, cast

from .exceptions import HybridMPlaneError

# Type variable for function return type
T = TypeVar('T')


class ErrorHandler:
    """
    A class for handling errors in a consistent way across the codebase.

    This class provides methods for logging errors with context information
    and converting generic exceptions to specific HybridMPlaneError types.
    """

    @staticmethod
    def log_error(
        error: Exception,
        level: int = logging.ERROR,
        include_traceback: bool = True,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        """
        Log an error with context information.

        Args:
            error: The exception to log.
            level: The logging level to use.
            include_traceback: Whether to include the traceback in the log.
            logger: The logger to use. If None, uses the root logger.
        """
        logger = logger or logging.getLogger()

        # Get the error message
        if isinstance(error, HybridMPlaneError):
            message = str(error)
        else:
            message = f"{type(error).__name__}: {str(error)}"

        # Log the error
        if include_traceback:
            logger.log(level, message, exc_info=sys.exc_info())
        else:
            logger.log(level, message)

    @staticmethod
    def handle_error(
        error: Exception,
        error_type: Type[HybridMPlaneError] = HybridMPlaneError,
        message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        log_level: int = logging.ERROR,
        include_traceback: bool = True,
        logger: Optional[logging.Logger] = None,
        reraise: bool = True,
    ) -> None:
        """
        Handle an error by logging it and optionally converting it to a specific error type.

        Args:
            error: The exception to handle.
            error_type: The type of HybridMPlaneError to convert to.
            message: A custom error message to use.
            context: Additional context information about the error.
            log_level: The logging level to use.
            include_traceback: Whether to include the traceback in the log.
            logger: The logger to use. If None, uses the root logger.
            reraise: Whether to reraise the error after handling it.

        Raises:
            HybridMPlaneError: The converted error, if reraise is True.
        """
        # If the error is already of the target type, just log it
        if isinstance(error, error_type):
            ErrorHandler.log_error(error, log_level, include_traceback, logger)
            if reraise:
                raise error
            return

        # Convert the error to the target type
        converted_error = error_type(message, context, error)

        # Log the converted error
        ErrorHandler.log_error(converted_error, log_level, include_traceback, logger)

        # Reraise the converted error if requested
        if reraise:
            raise converted_error


def log_error(
    error: Exception,
    level: int = logging.ERROR,
    include_traceback: bool = True,
    logger: Optional[logging.Logger] = None,
) -> None:
    """
    Log an error with context information.

    This is a convenience function that delegates to ErrorHandler.log_error.

    Args:
        error: The exception to log.
        level: The logging level to use.
        include_traceback: Whether to include the traceback in the log.
        logger: The logger to use. If None, uses the root logger.
    """
    ErrorHandler.log_error(error, level, include_traceback, logger)


def handle_error(
    error: Exception,
    error_type: Type[HybridMPlaneError] = HybridMPlaneError,
    message: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    log_level: int = logging.ERROR,
    include_traceback: bool = True,
    logger: Optional[logging.Logger] = None,
    reraise: bool = True,
) -> None:
    """
    Handle an error by logging it and optionally converting it to a specific error type.

    This is a convenience function that delegates to ErrorHandler.handle_error.

    Args:
        error: The exception to handle.
        error_type: The type of HybridMPlaneError to convert to.
        message: A custom error message to use.
        context: Additional context information about the error.
        log_level: The logging level to use.
        include_traceback: Whether to include the traceback in the log.
        logger: The logger to use. If None, uses the root logger.
        reraise: Whether to reraise the error after handling it.

    Raises:
        HybridMPlaneError: The converted error, if reraise is True.
    """
    ErrorHandler.handle_error(
        error, error_type, message, context, log_level, include_traceback, logger, reraise
    )


def with_error_handling(
    error_type: Type[HybridMPlaneError] = HybridMPlaneError,
    message: Optional[str] = None,
    context_provider: Optional[Callable[[Any, Any, Dict[str, Any]], Dict[str, Any]]] = None,
    log_level: int = logging.ERROR,
    include_traceback: bool = True,
    logger: Optional[Union[logging.Logger, str]] = None,
    reraise: bool = True,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for handling errors in functions.

    This decorator wraps a function with error handling logic that catches exceptions,
    logs them, and optionally converts them to specific HybridMPlaneError types.

    Args:
        error_type: The type of HybridMPlaneError to convert to.
        message: A custom error message to use.
        context_provider: A function that returns additional context information.
            It receives the function arguments and should return a dict.
        log_level: The logging level to use.
        include_traceback: Whether to include the traceback in the log.
        logger: The logger to use. If a string, gets the logger with that name.
            If None, uses the logger for the module of the decorated function.
        reraise: Whether to reraise the error after handling it.

    Returns:
        A decorator function.
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            # Get the logger
            nonlocal logger
            if logger is None:
                logger = logging.getLogger(func.__module__)
            elif isinstance(logger, str):
                logger = logging.getLogger(logger)

            # Get the context
            context = {}
            if context_provider:
                try:
                    context = context_provider(args, kwargs, context)
                except Exception as e:
                    # If the context provider fails, log it but continue
                    if isinstance(logger, logging.Logger):
                        logger.warning(f"Error in context provider: {e}")

            # Add function information to context
            context.update({
                'function': func.__name__,
                'module': func.__module__,
            })

            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Handle the error
                ErrorHandler.handle_error(
                    e, error_type, message, context, log_level, include_traceback, 
                    cast(Optional[logging.Logger], logger), reraise
                )
                # This will only be reached if reraise is False
                return cast(T, None)

        return wrapper

    return decorator
