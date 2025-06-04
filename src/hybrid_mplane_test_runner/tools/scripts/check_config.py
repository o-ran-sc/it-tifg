#!/usr/bin/env python3
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
Script to check that the configuration is loaded correctly.
"""

import logging
import sys
from hybrid_mplane_test_runner.config import get_config

def main():
    """Check that the configuration is loaded correctly."""
    # Set up logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    # Get the configuration
    config = get_config().get_config()

    # Print some configuration values
    print("\nConfiguration values:")
    print(f"Controller URL: {config.controller.odl_url}")
    print(f"Controller username: {config.controller.odl_username}")
    print(f"Controller password: {config.controller.odl_password}")
    print(f"Controller timeout: {config.controller.timeout}")
    print(f"Use simulator: {config.simulator.use_simulator}")
    print(f"Log level: {config.log_level}")

    # Check that the values match what's in default.json
    expected_values = {
        "controller.odl_url": "https://odlux.oam.smo.o-ran-sc.org",
        "controller.odl_username": "admin",
        "controller.odl_password": "Kp8bJ4SXszM0WXlhak3eHlcse2gAw84vaoGGmJvUy2U",
        "controller.timeout": 10,
        "simulator.use_simulator": True,
    }

    errors = []
    for path, expected in expected_values.items():
        parts = path.split(".")
        actual = config
        for part in parts:
            actual = getattr(actual, part)

        if actual != expected:
            errors.append(f"{path}: expected {expected}, got {actual}")

    if errors:
        print("\nErrors:")
        for error in errors:
            print(f"- {error}")
        sys.exit(1)
    else:
        print("\nAll values match what's in default.json!")
        sys.exit(0)

if __name__ == "__main__":
    main()
