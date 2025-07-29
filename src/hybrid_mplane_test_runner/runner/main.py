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

# File: runner/main.py
import json
import logging
import time
import os
import uuid
from datetime import datetime, UTC, timezone
from pathlib import Path
from typing import Optional, Any, List, Union, Dict

from hybrid_mplane_test_runner.runner.utils import TestResultsBase, ArchiveBuilder
from hybrid_mplane_test_runner.testcases.discovery import create_test_pipeline, TestDiscovery, TestExecutionPipeline
from hybrid_mplane_test_runner.tools.simulator import MPInterfaceSimulator
from hybrid_mplane_test_runner.oru_controller.opendaylight import OpenDaylightController
import hybrid_mplane_test_runner.models.testresult_models as models
from hybrid_mplane_test_runner.config import get_config
from hybrid_mplane_test_runner.errors import (
    HybridMPlaneError, ConfigurationError, SimulatorError, 
    handle_error, with_error_handling
)


@with_error_handling(error_type=ConfigurationError, message="Failed to set up logging")
def setup_logging(log_path: str) -> None:
    """
    Sets up logging configuration for the application using a file handler.
    The logs will be formatted in UTC, ensuring timestamp precision
    to the microsecond level.

    An internal logging formatter (UTCFormatter) is utilized to ensure
    that log timestamps are in UTC and formatted according to ISO 8601.
    This function ensures the log directory exists before initializing
    the log file, and raises an error in case of any configuration issue.

    :param log_path: The file path where log files will be saved. Directory
        structure will be created if it does not already exist.
    :type log_path: str
    :return: None
    :rtype: None
    :raises ConfigurationError: When the logging setup fails due to issues such
        as directory creation, or file write permissions. Error details will
        include the problematic log path and the underlying cause.
    """
    class UTCFormatter(logging.Formatter):
        converter = time.gmtime  # forces UTC for asctime

        def formatTime(self, record, datefmt=None):
            # Use datetime with UTC timezone for microsecond precision
            ct = datetime.fromtimestamp(record.created, tz=timezone.utc)
            if datefmt:
                s = ct.strftime(datefmt)
                return f"{s}.{ct.microsecond:06d}Z"
            else:
                return f"{ct.strftime('%Y-%m-%dT%H:%M:%S')}.{ct.microsecond:06d}Z"

    try:
        if os.path.dirname(log_path):
            os.makedirs(os.path.dirname(log_path), exist_ok=True)  # Ensure the log directory exists
        handler = logging.FileHandler(log_path)
        formatter = UTCFormatter(
            fmt="%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S"
        )
        handler.setFormatter(formatter)
        logging.root.handlers = [handler]
        logging.root.setLevel(logging.DEBUG)
        logging.info(f"Test runner started with config {get_config().get_config()}")
    except OSError as e:
        # More specific handling for file system related errors
        raise ConfigurationError(
            f"Failed to set up logging to {log_path}", 
            context={"log_path": log_path}, 
            cause=e
        )


@with_error_handling(error_type=ConfigurationError, message="Failed to load JSON file", reraise=False)
def load_json(path: str) -> List[dict]:
    """
    Load a JSON file from the specified path and return its content as a list of dictionaries.
    This function ensures appropriate error handling for file reading and JSON parsing issues.

    :param path: The file system path to the JSON file.
    :type path: str
    :return: A list of dictionaries representing the JSON content, or an empty list
        if there is an error in opening or parsing the file.
    :rtype: List[dict]
    """
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            # Handle JSON parsing errors
            handle_error(
                e, 
                ConfigurationError, 
                f"Invalid JSON format in '{path}'", 
                context={"path": path, "error_details": str(e)},
                reraise=False
            )
            return []
        except OSError as e:
            # Handle file system errors
            handle_error(
                e, 
                ConfigurationError, 
                f"Failed to read file '{path}'", 
                context={"path": path, "error_details": str(e)},
                reraise=False
            )
            return []
    return []


class HybridMPlaneTests(TestResultsBase):
    """
    HybridMPlaneTests represents a test initialization and metadata management class,
    inheriting from TestResultsBase. This class is responsible for managing test
    configurations, loading necessary metadata, and setting up paths for logging
    and results output. It centralizes test-specific metadata and provides access
    to testbed components, specifications, and result storage.

    This class aims to streamline the test setup process, ensuring all required
    data and paths are properly initialized and accessible for further test execution.

    :ivar testbed_components: A list of components in the testbed.
    :type testbed_components: List[models.TestbedComponent]
    :ivar test_lab: The test lab configuration metadata.
    :type test_lab: Optional[models.TestLab]
    :ivar test_specs: The specifications of tests to be executed.
    :type test_specs: List[models.TestSpecification]
    :ivar test_results: A list storing test results, including groups and individual
        cases.
    :type test_results: List[Union[models.TestGroup, models.TestCase]]
    :ivar test_id: A unique identifier for the test session, used for results
        output and logging.
    :type test_id: str
    :ivar timestamp: A UTC timestamp indicating the session start time, formatted
        as 'YYYYMMDDTHHMMSSZ'.
    :type timestamp: str
    :ivar paths: A dictionary holding paths for logs and results output.
    :type paths: Dict[str, str]
    :ivar test_metadata: Metadata specific to the current test session, including
        DUT details, test type, and contact information.
    :type test_metadata: models.TestMetadata
    """
    def __init__(self):
        super().__init__()
        config = get_config().get_config()

        # Load metadata files from configured paths
        metadata_dir = config.paths.metadata_dir
        testbed_raw = load_json(os.path.join(metadata_dir, config.paths.testbed_file))
        self.testbed_components = [models.TestbedComponent(**entry) for entry in testbed_raw]

        test_lab_raw = load_json(os.path.join(metadata_dir, config.paths.testlab_file))
        self.test_lab = models.TestLab(**test_lab_raw) if test_lab_raw else None

        test_specs_raw = load_json(os.path.join(metadata_dir, config.paths.specs_file))
        self.test_specs = [models.TestSpecification(**entry) for entry in test_specs_raw]

        self.test_results = []
        self.test_id = str(uuid.uuid4())
        self.timestamp = datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')

        # Use configured output directory
        output_dir = config.paths.output_dir
        self.paths = {
            "log_path": os.path.join(output_dir, f"log_{self.test_id}_{self.timestamp}.log"),
            "sim_log_path": os.path.join(output_dir, f"pynts-log_{self.test_id}_{self.timestamp}.log"),
            "restconf_log_path": os.path.join(output_dir, f"restconf-debug_{self.test_id}_{self.timestamp}.json"),
            "output_path": os.path.join(output_dir, f"results_{self.test_id}_{self.timestamp}.json")
        }
        setup_logging(self.paths["log_path"])

        # Use configured test metadata
        self.test_metadata = create_default_test_metadata(
                test_id=self.test_id,
                dut_name=config.test_metadata.dut_name,
                interface_under_test=[models.InterfaceUnderTest.o_ru_fhm],
                test_type=models.TestType.conformance,
                contacts=[
                    models.Contact(
                        firstName=config.test_metadata.contact_first_name,
                        lastName=config.test_metadata.contact_last_name,
                        email=config.test_metadata.contact_email,
                        organization=config.test_metadata.contact_organization,
                        phone=config.test_metadata.contact_phone
                    )
                ])

    @property
    def testMetadata(self) -> models.TestMetadata:
        return self.test_metadata

    @property
    def testbedComponents(self) -> List[models.TestbedComponent]:
        return self.testbed_components

    @property
    def testLab(self) -> models.TestLab:
        return self.test_lab

    @property
    def testSpecifications(self) -> List[models.TestSpecification]:
        return self.test_specs

    @property
    def testResults(self) -> List[Union[models.TestGroup, models.TestCase]]:
        return self.test_results

    @property
    def notes(self) -> Optional[List[models.TestNote]]:
        return None



@with_error_handling(error_type=SimulatorError, message="Failed to clean up environment", reraise=False)
def cleanup_environment(simulator: Optional[MPInterfaceSimulator]) -> None:
    """
    Clean up the simulation environment by stopping the provided simulator instance.
    This function is responsible for halting the simulator and handling any potential
    errors that may arise during the process. If no simulator is provided, the function
    exits without performing any actions. In case of an exception while stopping the
    simulator, the error is logged and managed based on the defined error handling
    parameters.

    :param simulator: The simulator interface instance to be cleaned up. Accepts an
        object conforming to the MPInterfaceSimulator type or None.
    :type simulator: Optional[MPInterfaceSimulator]
    :return: None
    """
    if not simulator:
        return
    try:
        simulator.stop()
    except Exception as e:
        handle_error(
            e,
            SimulatorError,
            "Could not stop simulator",
            context={"simulator_type": type(simulator).__name__},
            log_level=logging.WARNING,
            reraise=False
        )


def create_default_test_metadata(
        test_id: str,
        dut_name: str = None,
        interface_under_test: Optional[list[models.InterfaceUnderTest]] = None,
        test_type: models.TestType = models.TestType.conformance,
        contacts: Optional[List[models.Contact]] = None,
        config_params: Optional[models.ConfigurationParameters] = None
) -> models.TestMetadata:
    """
    Creates and initializes a default test metadata object using provided values
    or defaults from the configuration. This function allows the creation of
    metadata for a test, containing details about the device under test (DUT),
    test execution parameters, and additional configuration settings.

    The test metadata includes information such as test type, interface under
    test, contact information, start and stop timestamps, and configuration
    parameters. Default values for some attributes are fetched from the
    application configuration if they are not provided in the arguments.

    :param test_id: A unique identifier for the test.
    :type test_id: str
    :param dut_name: The name of the device under test (DUT). If not provided,
        default is fetched from configuration.
    :type dut_name: str, optional
    :param interface_under_test: A list of interfaces being tested. If not provided,
        defaults to [models.InterfaceUnderTest.o_ru_fhm].
    :type interface_under_test: Optional[list[models.InterfaceUnderTest]], optional
    :param test_type: The type of test being executed. Defaults to conformance.
    :type test_type: models.TestType, optional
    :param contacts: A list of contact objects representing individuals
        associated with the test. If not provided, defaults to a contact derived
        from configuration.
    :type contacts: Optional[List[models.Contact]], optional
    :param config_params: Configuration parameters related to the test execution.
        If not provided, defaults to specific preset configuration parameters.
    :type config_params: Optional[models.ConfigurationParameters], optional

    :return: A populated TestMetadata object with the provided or default
        attributes.
    :rtype: models.TestMetadata
    """
    # Load configuration
    config = get_config().get_config()

    # Use configured values or provided values
    if dut_name is None:
        dut_name = config.test_metadata.dut_name

    current_time = datetime.now(UTC).isoformat()
    return models.TestMetadata(
        dutName=dut_name,
        testType=test_type,
        interfaceUnderTest=interface_under_test or [models.InterfaceUnderTest.o_ru_fhm],
        startDate=current_time,
        stopDate=current_time,
        result=models.ResultType.FAIL,
        testId=test_id,
        contacts=contacts or [
            models.Contact(
                firstName=config.test_metadata.contact_first_name,
                lastName=config.test_metadata.contact_last_name,
                email=config.test_metadata.contact_email,
                organization=config.test_metadata.contact_organization,
                phone=config.test_metadata.contact_phone
            )
        ],
        configurationParameters=config_params or models.ConfigurationParameters(
            ipv4=True,
            ipv6=False,
            duplexMode=models.DuplexMode.tdd,
            deploymentArchitecture=models.DeploymentArchitecture.indoor,
            deploymentScale=models.DeploymentScale.micro,
            deploymentRfScenario=models.DeploymentRfScenario.urban
        )
    )


@with_error_handling(error_type=HybridMPlaneError, message="Failed to serialize results")
def serialize_results(full_result: Any, output_path: str) -> None:
    """
    Serializes the provided result data into a JSON file, handling both primary and fallback
    serialization methods to ensure reliability. Designed to handle potential serialization
    failures gracefully by using a fallback method and propagating detailed errors if both
    attempts fail. Logs warnings upon primary serialization failure and raises a custom error
    with additional context for any complete failure.

    :param full_result: The data object to serialize. Expected to implement `model_dump_json`
        and `model_dump` methods for JSON serialization.
    :type full_result: Any
    :param output_path: The file path where the serialized JSON output should be stored.
    :type output_path: str
    :return: None
    """
    try:
        with open(output_path, "w") as f:
            f.write(full_result.model_dump_json(indent=2, exclude_none=True, by_alias=True))
    except Exception as e:
        # Log the primary serialization failure but don't raise yet
        handle_error(
            e,
            HybridMPlaneError,
            "Primary serialization method failed",
            context={"output_path": output_path, "result_type": type(full_result).__name__},
            log_level=logging.WARNING,
            reraise=False
        )

        # Try the fallback serialization method
        try:
            with open(output_path, "w") as f:
                json.dump(full_result.model_dump(exclude_none=True, by_alias=True), f, indent=2)
        except Exception as fallback_error:
            # If the fallback also fails, raise a more detailed error
            raise HybridMPlaneError(
                "Both primary and fallback serialization methods failed",
                context={
                    "output_path": output_path,
                    "result_type": type(full_result).__name__,
                    "primary_error": str(e),
                    "fallback_error": str(fallback_error)
                },
                cause=fallback_error
            )


@with_error_handling(error_type=HybridMPlaneError, message="Test execution failed")
def main() -> None:
    """
    Executes the main function to orchestrate the loading of configuration, initializing test
    objects, controllers, simulators, and running test pipelines based on the defined configuration.
    Handles artifact generation and serializing the test results to JSON. The function also ensures
    proper logging and manages error handling for critical processes like log collection.

    :return: None
    """
    # Load configuration
    config = get_config().get_config()

    # Set up logging level
    logging.root.setLevel(getattr(logging, config.log_level))

    test_object = HybridMPlaneTests()

    # Initialize controller with configuration
    odl_controller = OpenDaylightController(
        base_url=config.controller.odl_url,
        username=config.controller.odl_username,
        password=config.controller.odl_password,
        timeout=config.controller.timeout
    )

    # Initialize simulator if configured
    simulator = MPInterfaceSimulator() if config.simulator.use_simulator else None

    if simulator:
        simulator.start()


    test_object.test_metadata.startDate = datetime.now(UTC)

    result_status = models.ResultType.PASS

    # Create test discovery and execution pipeline
    discovery, pipeline = create_test_pipeline()

    # Add global setup hook for simulator initialization
    if simulator:
        pipeline.add_global_setup_hook(lambda: logging.info("Global setup: Simulator already initialized"))

    # Add global teardown hook for simulator cleanup
    if simulator:
        pipeline.add_global_teardown_hook(lambda: logging.info("Global teardown: Simulator will be cleaned up later"))

    # Get test execution configuration
    config = get_config().get_config()

    # Execute tests based on configuration
    all_results = []

    # Check if specific test cases are configured
    if hasattr(config, 'test_execution') and hasattr(config.test_execution, 'test_cases'):
        # Run specific test cases
        test_case_ids = config.test_execution.test_cases
        logging.info(f"Running specific test cases: {test_case_ids}")

        # Run selected test cases and get a TestGroup result
        selected_group = pipeline.run_selected_test_cases(test_case_ids, odl_controller)

        # Add the TestGroup directly to test results
        test_object.test_results.append(selected_group)

        # Also add individual test cases to all_results for artifact processing
        for test_case in selected_group.groupItems:
            if isinstance(test_case, models.TestCase):
                all_results.append(test_case)

    # Check if specific categories are configured
    elif hasattr(config, 'test_execution') and hasattr(config.test_execution, 'categories'):
        # Run test cases by category
        categories = config.test_execution.categories
        logging.info(f"Running test cases in categories: {categories}")
        for category in categories:
            # Run test cases in the category and get a TestGroup result
            category_group = pipeline.run_test_cases_by_category(category, odl_controller)

            # Add the TestGroup directly to test results
            test_object.test_results.append(category_group)

            # Also add individual test cases to all_results for artifact processing
            for test_case in category_group.groupItems:
                if isinstance(test_case, models.TestCase):
                    all_results.append(test_case)

    # Check if specific suites are configured
    elif hasattr(config, 'test_execution') and hasattr(config.test_execution, 'suites'):
        # Run specific test suites
        suite_names = config.test_execution.suites
        logging.info(f"Running test suites: {suite_names}")
        for suite_name in suite_names:
            suite = discovery.get_test_suite(suite_name)
            if suite:
                # Run the test suite and get a TestGroup result
                test_group = pipeline.run_test_suite(suite, odl_controller)

                # Add the TestGroup directly to test results
                test_object.test_results.append(test_group)

                # Also add individual test cases to all_results for artifact processing
                for test_case in test_group.groupItems:
                    if isinstance(test_case, models.TestCase):
                        all_results.append(test_case)
            else:
                logging.warning(f"Test suite '{suite_name}' not found")

    # Default: run all discovered test cases
    else:
        logging.info("Running all discovered test cases")
        test_groups = pipeline.run_all_test_suites(odl_controller)

        # Add all TestGroup objects directly to test results
        for test_group in test_groups:
            test_object.test_results.append(test_group)

            # Also add individual test cases to all_results for artifact processing
            for test_case in test_group.groupItems:
                if isinstance(test_case, models.TestCase):
                    all_results.append(test_case)

    # Process test results
    for tc_result in all_results:
        if tc_result.result == models.ResultType.FAIL:
            result_status = models.ResultType.FAIL

        # Create artifacts list
        artifacts = [
            models.Artifact(
                name="Execution Log",
                description="Log of the test runner execution",
                path=test_object.paths["log_path"].replace("output/", "")
            ),
            models.Artifact(
                name="RESTCONF Request/Response",
                description="Raw RESTCONF exchange with OpenDaylight controller",
                path=test_object.paths["restconf_log_path"].replace("output/", "")
            )
        ]

        if simulator:
            artifacts.append(
                models.Artifact(
                    name="Simulator Log",
                    description="Log collected from inside the simulator container",
                    path=test_object.paths["sim_log_path"].replace("output/", "")
                )
            )

        # Assign artifacts directly through the Pydantic model
        tc_result.artifacts = models.Artifacts(artifacts)

        # Note: We don't append tc_result to test_object.test_results here
        # because test cases are already included in their respective test groups

    test_object.test_metadata.result = result_status

    try:
        with open(test_object.paths["restconf_log_path"], "w") as f:
            json.dump(odl_controller.get_debug_log(), f, indent=2)
    except Exception as e:
        handle_error(
            e,
            HybridMPlaneError,
            "Failed to collect RESTCONF debug log",
            context={"log_path": test_object.paths["restconf_log_path"]},
            log_level=logging.WARNING,
            reraise=False
        )

    test_object.test_metadata.stopDate = datetime.now(UTC)

    if simulator:
        try:
            simulator.collect_logs(test_object.paths["sim_log_path"])
        except Exception as e:
            handle_error(
                e,
                SimulatorError,
                "Could not collect simulator logs",
                context={
                    "simulator_type": type(simulator).__name__,
                    "log_path": test_object.paths["sim_log_path"]
                },
                log_level=logging.WARNING,
                reraise=False
            )
        # No cleanup currently, we just want to run other tests that are assuming that the connection is already there
        # cleanup_environment(simulator)

    # Create archive builder
    archive_builder = ArchiveBuilder()
    archive_builder.set_results(test_object.testResultsSummary)

    # Include artifacts in the archive
    archive_builder.include_artifact(
        Path(test_object.paths["log_path"]), 
        Path(os.path.basename(test_object.paths["log_path"])), 
        "Execution Log", 
        "Log of the test runner execution"
    )

    archive_builder.include_artifact(
        Path(test_object.paths["restconf_log_path"]), 
        Path(os.path.basename(test_object.paths["restconf_log_path"])), 
        "RESTCONF Request/Response", 
        "Raw RESTCONF exchange with OpenDaylight controller"
    )

    if simulator:
        archive_builder.include_artifact(
            Path(test_object.paths["sim_log_path"]), 
            Path(os.path.basename(test_object.paths["sim_log_path"])), 
            "Simulator Log", 
            "Log collected from inside the simulator container"
        )

    # Check if we should skip archiving
    if config.skip_archiving:
        # Save results directly without archiving
        results_path = os.path.join(os.path.dirname(test_object.paths["output_path"]), f"results_{test_object.test_id}_{test_object.timestamp}.json")
        with open(results_path, "w") as f:
            f.write(test_object.testResultsSummary.model_dump_json(exclude_none=True, by_alias=True))

        print(f"Tests finished with an overall status of {result_status}")
        print(f"Results saved to: {results_path}")
        print(f"Artifacts saved to: {os.path.dirname(test_object.paths['output_path'])}")
    else:
        # Export the archive
        archive_path = os.path.join(os.path.dirname(test_object.paths["output_path"]), f"results_{test_object.test_id}_{test_object.timestamp}.zip")
        archive_builder.export_archive(Path(archive_path))

        # Remove the individual files after archiving
        try:
            os.remove(test_object.paths["log_path"])
            os.remove(test_object.paths["restconf_log_path"])
            if simulator:
                os.remove(test_object.paths["sim_log_path"])
            # We don't need to create the separate results*.json file
            # The results.json is already included in the archive
        except Exception as e:
            handle_error(
                e,
                HybridMPlaneError,
                "Failed to remove individual log files",
                context={"error_details": str(e)},
                log_level=logging.WARNING,
                reraise=False
            )

        print(f"Tests finished with an overall status of {result_status}")
        print(f"Results and artifacts archived to: {archive_path}")


if __name__ == "__main__":
    main()
