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
Custom exception classes for the Hybrid M-Plane Test Runner.

This module defines a hierarchy of exception classes that can be used
throughout the codebase to provide consistent error handling and reporting.
"""

class HybridMPlaneError(Exception):
    """Base exception class for all Hybrid M-Plane Test Runner errors."""

    def __init__(self, message=None, context=None, cause=None):
        """
        Initialize a new HybridMPlaneError.

        Args:
            message (str, optional): Human-readable error message.
            context (dict, optional): Additional context information about the error.
            cause (Exception, optional): The original exception that caused this error.
        """
        self.message = message or "An error occurred in the Hybrid M-Plane Test Runner"
        self.context = context or {}
        self.cause = cause

        # Build the full error message with context information
        full_message = self.message
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            full_message = f"{full_message} [Context: {context_str}]"
        if self.cause:
            full_message = f"{full_message} [Caused by: {type(self.cause).__name__}: {str(self.cause)}]"

        super().__init__(full_message)


class ConfigurationError(HybridMPlaneError):
    """Exception raised for errors related to configuration."""

    def __init__(self, message=None, context=None, cause=None):
        message = message or "Configuration error"
        super().__init__(message, context, cause)


class ControllerError(HybridMPlaneError):
    """Exception raised for errors related to the controller."""

    def __init__(self, message=None, context=None, cause=None):
        message = message or "Controller error"
        super().__init__(message, context, cause)


class TestCaseError(HybridMPlaneError):
    """Exception raised for errors related to test cases."""

    def __init__(self, message=None, context=None, cause=None):
        message = message or "Test case error"
        super().__init__(message, context, cause)


class SimulatorError(HybridMPlaneError):
    """Exception raised for errors related to the simulator."""

    def __init__(self, message=None, context=None, cause=None):
        message = message or "Simulator error"
        super().__init__(message, context, cause)


class NetworkError(HybridMPlaneError):
    """Exception raised for network-related errors."""

    def __init__(self, message=None, context=None, cause=None):
        message = message or "Network error"
        super().__init__(message, context, cause)


class TimeoutError(HybridMPlaneError):
    """Exception raised when an operation times out."""

    def __init__(self, message=None, context=None, cause=None):
        message = message or "Operation timed out"
        super().__init__(message, context, cause)


class ValidationError(HybridMPlaneError):
    """Exception raised for validation errors."""

    def __init__(self, message=None, context=None, cause=None):
        message = message or "Validation error"
        super().__init__(message, context, cause)
