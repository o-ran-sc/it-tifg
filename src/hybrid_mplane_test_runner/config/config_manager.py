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
Configuration manager for Hybrid M-Plane Test Runner.

This module provides a centralized configuration system that loads configuration
from files and environment variables, validates it, and provides access to it.
"""

import os
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union, List, Type
from pydantic import BaseModel, Field, ValidationError


class PathConfig(BaseModel):
    """Configuration for file paths used in the application."""

    metadata_dir: str = Field(default="metadata", description="Directory containing metadata files")
    output_dir: str = Field(default="output", description="Directory for output files")
    testbed_file: str = Field(default="testbed.json", description="Testbed metadata file name")
    testlab_file: str = Field(default="testlab.json", description="Test lab metadata file name")
    specs_file: str = Field(default="specs.json", description="Test specifications file name")
    results_file: str = Field(default="results.json", description="Results file name")


class TestMetadataConfig(BaseModel):
    """Configuration for test metadata defaults."""

    dut_name: str = Field(default="PyNTS O-RU", description="Default Device Under Test name")
    contact_first_name: str = Field(default="Alice", description="Default contact first name")
    contact_last_name: str = Field(default="Tester", description="Default contact last name")
    contact_email: str = Field(default="alice@example.org", description="Default contact email")
    contact_organization: str = Field(default="ExampleOrg", description="Default contact organization")
    contact_phone: str = Field(default="+123456789", description="Default contact phone")


class TestCaseConfig(BaseModel):
    """Configuration for test cases."""

    tc_001_expected_name: str = Field(default="pynts-o-ru-hybrid", description="Expected node name for TC-001")
    tc_001_expected_status: str = Field(default="connected", description="Expected status for TC-001")
    tc_001_expected_capability: str = Field(default="o-ran-uplane-conf", description="Expected capability for TC-001")

    # TC-002 configuration
    tc_002_mountpoint_name: str = Field(default="pynts-o-ru-hybrid", description="Mountpoint name for TC-002")
    tc_002_filter_path: str = Field(default="network-topology:network-topology/topology=topology-netconf", 
                                   description="Path for subtree-filtered data retrieval in TC-002")
    tc_002_config_path: str = Field(default="network-topology:network-topology/topology=topology-netconf", 
                                   description="Path for configuration-only data retrieval in TC-002")

    # TC-003 configuration
    tc_003_mountpoint_name: str = Field(default="pynts-o-ru-hybrid", description="Mountpoint name for TC-003")


class ControllerConfig(BaseModel):
    """Configuration for controllers."""

    odl_url: str = Field(default="https://odlux.oam.smo.o-ran-sc.org", description="OpenDaylight controller URL")
    odl_username: str = Field(default="admin", description="OpenDaylight username")
    odl_password: str = Field(default="Kp8bJ4SXszM0WXlhak3eHlcse2gAw84vaoGGmJvUy2U", description="OpenDaylight password")
    timeout: int = Field(default=10, description="Controller request timeout in seconds")


class SimulatorConfig(BaseModel):
    """Configuration for simulators."""

    use_simulator: bool = Field(default=True, description="Whether to use the simulator")
    simulator_image: str = Field(default="pynts-oru:latest", description="Simulator Docker image")
    simulator_port: int = Field(default=830, description="Simulator NETCONF port")


class TestExecutionConfig(BaseModel):
    """Configuration for test execution."""

    test_cases: Optional[List[str]] = Field(default=None, description="List of test case IDs to run")
    categories: Optional[List[str]] = Field(default=None, description="List of test categories to run")
    suites: Optional[List[str]] = Field(default=None, description="List of test suites to run")


class AppConfig(BaseModel):
    """Main application configuration."""

    paths: PathConfig = Field(default_factory=PathConfig, description="Path configuration")
    test_metadata: TestMetadataConfig = Field(default_factory=TestMetadataConfig, description="Test metadata configuration")
    test_cases: TestCaseConfig = Field(default_factory=TestCaseConfig, description="Test case configuration")
    controller: ControllerConfig = Field(default_factory=ControllerConfig, description="Controller configuration")
    simulator: SimulatorConfig = Field(default_factory=SimulatorConfig, description="Simulator configuration")
    log_level: str = Field(default="INFO", description="Logging level")
    test_execution: Optional[TestExecutionConfig] = Field(default=None, description="Test execution configuration")
    skip_archiving: bool = Field(default=False, description="If True, results will not be archived in a zip file but saved directly")


class ConfigManager:
    """
    Configuration manager for the application.

    This class is responsible for loading, validating, and providing access to
    configuration values from files and environment variables.
    """

    _instance = None
    _config = None

    def __new__(cls, *args, **kwargs):
        """Implement singleton pattern."""
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, config_file: Optional[str] = None, env_prefix: str = "HMP_"):
        """
        Initialize the configuration manager.

        Args:
            config_file: Path to the configuration file. If None, default configuration values are used.
                         When using get_config(), if config_file is None, it will try to load config/default.json.
            env_prefix: Prefix for environment variables that override configuration values.
        """
        if self._initialized:
            return

        self._config_file = config_file
        self._env_prefix = env_prefix
        self._config = self._load_config()
        self._initialized = True

    def _load_config(self) -> AppConfig:
        """
        Load configuration from file and environment variables.

        Returns:
            AppConfig: The loaded and validated configuration.
        """
        # Start with default configuration
        config_dict = AppConfig().model_dump()

        # Load from file if provided
        if self._config_file:
            if os.path.exists(self._config_file):
                try:
                    logging.info(f"Loading configuration from '{self._config_file}'")
                    with open(self._config_file, "r") as f:
                        file_config = json.load(f)
                    # Update config with values from file
                    self._update_nested_dict(config_dict, file_config)
                    logging.info(f"Successfully loaded configuration from '{self._config_file}'")
                except (json.JSONDecodeError, OSError) as e:
                    logging.warning(f"Failed to load configuration from '{self._config_file}': {e}")
            else:
                logging.warning(f"Configuration file '{self._config_file}' does not exist")

        # Override with environment variables
        self._override_from_env(config_dict)

        # Validate and create config object
        try:
            return AppConfig(**config_dict)
        except ValidationError as e:
            logging.error(f"Configuration validation failed: {e}")
            # Fall back to default configuration
            return AppConfig()

    def _update_nested_dict(self, target: Dict, source: Dict) -> None:
        """
        Update a nested dictionary with values from another dictionary.

        Args:
            target: The dictionary to update.
            source: The dictionary with values to use for the update.
        """
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._update_nested_dict(target[key], value)
            else:
                target[key] = value

    def _override_from_env(self, config_dict: Dict) -> None:
        """
        Override configuration values with values from environment variables.

        Environment variables should be in the format:
        {ENV_PREFIX}_{SECTION}_{KEY} (e.g., HMP_PATHS_OUTPUT_DIR)

        Args:
            config_dict: The configuration dictionary to update.
        """
        for env_var, env_value in os.environ.items():
            if not env_var.startswith(self._env_prefix):
                continue

            # Remove prefix and split into parts
            parts = env_var[len(self._env_prefix):].lower().split('_')
            if len(parts) < 2:
                continue

            # Navigate to the correct section in the config
            current = config_dict
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]

            # Set the value, converting to appropriate type
            key = parts[-1]
            if key in current:
                # Try to convert to the same type as the existing value
                try:
                    if isinstance(current[key], bool):
                        current[key] = env_value.lower() in ('true', 'yes', '1')
                    elif isinstance(current[key], int):
                        current[key] = int(env_value)
                    elif isinstance(current[key], float):
                        current[key] = float(env_value)
                    else:
                        current[key] = env_value
                except (ValueError, TypeError):
                    logging.warning(f"Failed to convert environment variable {env_var} to appropriate type")
                    current[key] = env_value
            else:
                current[key] = env_value

    def get_config(self) -> AppConfig:
        """
        Get the application configuration.

        Returns:
            AppConfig: The application configuration.
        """
        return self._config

    def get(self, section: str, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.

        Args:
            section: The configuration section.
            key: The configuration key.
            default: The default value to return if the key is not found.

        Returns:
            The configuration value, or the default if not found.
        """
        try:
            return getattr(getattr(self._config, section), key)
        except AttributeError:
            return default


# Global instance for easy access
_config_manager = None


def get_config(config_file: Optional[str] = None, env_prefix: str = "HMP_") -> ConfigManager:
    """
    Get the global configuration manager instance.

    Args:
        config_file: Path to the configuration file. If None, default.json is used.
        env_prefix: Prefix for environment variables that override configuration values.

    Returns:
        ConfigManager: The global configuration manager instance.
    """
    global _config_manager
    if _config_manager is None:
        # If no config file is provided, use the default.json
        if config_file is None:
            default_config = os.path.join("config", "default.json")
            if os.path.exists(default_config):
                logging.info(f"Using default configuration file: '{default_config}'")
                config_file = default_config
            else:
                logging.warning(f"Default configuration file '{default_config}' not found. Using built-in defaults.")
        _config_manager = ConfigManager(config_file, env_prefix)
    return _config_manager
