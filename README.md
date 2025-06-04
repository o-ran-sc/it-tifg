# TIFG

An open-source Python-based test runner for executing and reporting Hybrid M-Plane conformance tests for O-RUs, compliant with O-RAN Alliance standards.

## Requirements
- Python 3.12 (default in Ubuntu 24.04)

## Setup

### 1. Clone the repository
```bash
git clone "https://gerrit.o-ran-sc.org/r/it/tifg"
cd tifg
```

### 2. Create and activate a virtual environment
```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

## Run a Test Case
You can run the test runner either manually or via `make`:

### Option 1: Manual
```bash
PYTHONPATH=src python3.12 -m hybrid_mplane_test_runner.runner.main
```

### Option 2: Using Makefile
```bash
make run        # Run the test cases defined in config
make venv       # Create a virtual environment
make clean      # Clean up output files
make viz-start  # Start visualization services (Grafana and TimescaleDB)
make viz-stop   # Stop visualization services
```

The results will be saved under the `output/` directory as a JSON file conforming to the official O-RAN test results schema.

## Configuration
The test runner can be configured using a JSON configuration file and/or environment variables.

### Configuration File
By default, the test runner looks for a configuration file at `config/default.json`. You can also specify a custom configuration file using the `--config` command-line option:

```bash
PYTHONPATH=src python3.12 -m hybrid_mplane_test_runner.runner.main --config my_config.json
```

Alternatively, you can use a `.env` file (e.g., `config.env`) to set environment variables for configuration.

### Selecting Test Cases to Run
You can specify which test cases to run in the configuration file under the `test_execution` section:

```json
"test_execution": {
  "test_cases": ["002", "003"],     // Run specific test cases by ID
  "_categories": ["basic"],         // Run test cases by category (commented out)
  "_suites": ["Default"]            // Run test cases by suite (commented out)
}
```

Uncomment and modify the desired option to control which tests are executed.

### Configuration Options
The configuration file is organized into sections:

- **paths**: Directories and file paths for metadata and output
- **test_metadata**: Default metadata for test reports
- **test_cases**: Configuration for individual test cases
- **controller**: NETCONF controller connection settings
- **simulator**: O-RU simulator settings
- **log_level**: Logging verbosity
- **test_execution**: Test case selection

### Environment Variable Overrides
Any configuration option can be overridden using environment variables with the prefix `HMP_` followed by the section and key in uppercase, separated by underscores:

```bash
# Override controller URL
export HMP_CONTROLLER_ODL_URL="https://my-controller.example.org"

# Enable simulator
export HMP_SIMULATOR_USE_SIMULATOR=true

# Run specific test cases
export HMP_TEST_EXECUTION_TEST_CASES='["001", "002", "003"]'
```

### Example Configuration
Here's an example of a minimal configuration file that runs test cases 002 and 003 against a specific controller:

```json
{
  "controller": {
    "odl_url": "https://my-controller.example.org",
    "odl_username": "admin",
    "odl_password": "my-password"
  },
  "test_execution": {
    "test_cases": ["002", "003"]
  }
}
```

For a complete list of configuration options, refer to the default configuration file at `config/default.json`.

## Project Structure
```
tifg/
├── src/                         # Source code lives here
│   └── hybrid_mplane_test_runner/
│       ├── testcases/          # Individual test case logic
│       └── runner/             # Runner logic and result construction
├── config/                      # Configuration files
│   └── default.json            # Default configuration values
├── metadata/                   # Static metadata (testbed, contacts, etc.)
│   ├── environment.json        # DUT, interface, configuration (no dynamic results)
│   └── testlab.json            # Test lab details
├── output/                     # Generated results
├── schema/                     # O-RAN test results JSON schema
├── docs/                       # Test procedure descriptions
├── visualization/              # Test results visualization solution
│   ├── grafana/                # Grafana dashboards and configuration
│   ├── init-scripts/           # Database initialization scripts
│   ├── docker-compose.yml      # Docker Compose for TimescaleDB and Grafana
│   └── README.md               # Visualization setup instructions
├── requirements.txt            # Python dependencies
├── config.env                  # (Optional) Environment variables for configuration
├── LICENSE                     # Apache License 2.0
├── Makefile                    # Helper commands for running and cleaning
└── README.md                   # Project info (this file)
```

## License
Licensed under the [Apache License 2.0](LICENSES).

## Visualization
The test runner provides several ways to visualize and analyze test results:

### Current Capabilities
- **JSON Output**: Test results are saved as structured JSON files in the `output/` directory
- **Jupyter Notebooks**: 
  - `Generic_Hybrid_MPlane_Test_Runner.ipynb`: A flexible notebook that can run any test case with interactive configuration, execution, and visualization
  - `Hybrid_MPlane_TestCase_Connection.ipynb`: A notebook specific to TestCase 001 (NETCONF Connection Establishment)
- **Console Logging**: Detailed test execution logs are displayed in the console during test runs
- **Grafana & TimescaleDB**: The `visualization/` folder contains a complete solution for advanced test results visualization:
  - **TimescaleDB**: A time-series database for storing and querying test results data
  - **Grafana Dashboards**: Pre-configured dashboards for visualizing test metrics and trends
  - **Automated Data Ingestion**: Service that automatically processes test results and stores them in the database
  - **Easy Start/Stop**: Use `make viz-start` to start the visualization services and `make viz-stop` to stop them
  - See the [visualization/README.md](visualization/README.md) for detailed setup instructions and more information

### Planned Enhancements
- Support for multiple output formats (JSON, XML, HTML)
- Advanced visualization capabilities for test results
- Web-based dashboard with real-time test status updates and historical results visualization

## Containerization
A `Dockerfile` for containerized execution will be added in the future.
