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

import os
import sys
import logging

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Import the configuration manager
from hybrid_mplane_test_runner.config import get_config

def test_default_config():
    """Test that the default configuration is loaded correctly."""
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
    assert config.controller.odl_url == "https://odlux.oam.smo.o-ran-sc.org", "Controller URL doesn't match default.json"
    assert config.controller.odl_username == "admin", "Controller username doesn't match default.json"
    assert config.controller.odl_password == "Kp8bJ4SXszM0WXlhak3eHlcse2gAw84vaoGGmJvUy2U", "Controller password doesn't match default.json"
    assert config.controller.timeout == 10, "Controller timeout doesn't match default.json"
    assert config.simulator.use_simulator == True, "Use simulator doesn't match default.json"
    
    print("\nAll tests passed! The default configuration is loaded correctly.")

if __name__ == "__main__":
    test_default_config()