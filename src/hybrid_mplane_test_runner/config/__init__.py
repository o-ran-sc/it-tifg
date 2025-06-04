"""
Configuration management module for Hybrid M-Plane Test Runner.

This module provides a centralized configuration system for the application,
replacing hardcoded values and environment variables with a more flexible
and maintainable approach.
"""

from hybrid_mplane_test_runner.config.config_manager import ConfigManager, get_config

__all__ = ["ConfigManager", "get_config"]