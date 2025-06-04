# Configuration Management System

This directory contains configuration files for the Hybrid M-Plane Test Runner. The configuration system allows you to customize the behavior of the test runner without modifying the code.

## Configuration Files

- `default.json`: Default configuration values. This file is automatically loaded when no custom configuration file is specified. It should not be modified directly for normal operation. Instead, create a custom configuration file and specify it when running the test runner.

## Configuration Structure

The configuration is organized into the following sections:

### Paths

Configuration for file paths used in the application:

```json
"paths": {
  "metadata_dir": "metadata",
  "output_dir": "output",
  "testbed_file": "testbed.json",
  "testlab_file": "testlab.json",
  "specs_file": "specs.json",
  "results_file": "results.json"
}
```

### Test Metadata

Configuration for test metadata defaults:

```json
"test_metadata": {
  "dut_name": "PyNTS O-RU",
  "contact_first_name": "Alice",
  "contact_last_name": "Tester",
  "contact_email": "alice@example.org",
  "contact_organization": "ExampleOrg",
  "contact_phone": "+123456789"
}
```

### Test Cases

Configuration for test cases:

```json
"test_cases": {
  "tc_001_expected_name": "pynts-o-ru-hybrid",
  "tc_001_expected_status": "connected",
  "tc_001_expected_capability": "o-ran-uplane-conf"
}
```

### Controller

Configuration for controllers:

```json
"controller": {
  "odl_url": "http://localhost:8181",
  "odl_username": "admin",
  "odl_password": "admin",
  "timeout": 30
}
```

### Simulator

Configuration for simulators:

```json
"simulator": {
  "use_simulator": false,
  "simulator_image": "pynts-oru:latest",
  "simulator_port": 830
}
```

### Logging

Configuration for logging:

```json
"log_level": "INFO"
```

## Using Custom Configuration

You can specify a custom configuration file when running the test runner:

```python
from hybrid_mplane_test_runner.config import get_config

# Initialize configuration with a custom file
config_manager = get_config("/path/to/custom/config.json")
```

## Verifying Configuration

You can verify that the configuration is loaded correctly by running:

```bash
make check-config
```

This will print the current configuration values and check that they match what's expected in the default.json file.

## Environment Variables

You can also override configuration values using environment variables. The environment variables should be in the format:

```
HMP_<SECTION>_<KEY>
```

For example:

```
HMP_PATHS_OUTPUT_DIR=/custom/output/dir
HMP_CONTROLLER_ODL_URL=http://custom-controller:8181
HMP_SIMULATOR_USE_SIMULATOR=true
```

Environment variables take precedence over values in configuration files.

## Accessing Configuration Values

To access configuration values in your code:

```python
from hybrid_mplane_test_runner.config import get_config

# Get the configuration manager
config = get_config()

# Access configuration values
output_dir = config.get_config().paths.output_dir
use_simulator = config.get_config().simulator.use_simulator

# Or use the get method
output_dir = config.get("paths", "output_dir")
use_simulator = config.get("simulator", "use_simulator")
```
