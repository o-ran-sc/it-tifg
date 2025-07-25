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

from typing import Iterable, Dict, Any
import json

from hybrid_mplane_test_runner.testcases.base import HybridMPlaneTestCase
from hybrid_mplane_test_runner.oru_controller.base import ORUController
import hybrid_mplane_test_runner.models.testresult_models as models
from requests.exceptions import ReadTimeout
import logging
from datetime import datetime, UTC
from hybrid_mplane_test_runner.config import get_config


class TestCase_002(HybridMPlaneTestCase):
    """
    Manages the execution of Test Case 002.

    This class represents a test case that verifies the O-RU exposes operational and configuration data 
    via NETCONF and that the O-RU Controller retrieves and exposes this data using RESTCONF in JSON format.
    It performs three types of read-only retrievals:
    1. Full data tree (unfiltered)
    2. Subtree-filtered data
    3. Configuration-only data (i.e., read-write nodes)

    :ivar tc_model: A representation of the test case model holding details such as notes,
        start date, stop date, result, and metrics.
    :type tc_model: models.TestCase
    :ivar number: Identifier for the test case, in this specific case "002".
    :type number: str
    :ivar name: Full name or descriptive title for the test case.
    :type name: str
    :ivar controller: The ORUController instance used for managing network operations during
        the test case execution.
    :type controller: ORUController
    :ivar categories: List of categories this test case belongs to.
    :type categories: List[str]
    :ivar suite: Name of the test suite this test case belongs to.
    :type suite: str
    """
    # Define categories and suite for test discovery
    categories = ["basic", "data", "restconf"]
    suite = "Data Retrieval"
    ERROR_TIMEOUT = "Connection to controller timed out"

    def __init__(self, controller: ORUController = None):
        super().__init__("002",
                         "Read-Only Data Retrieval (Unfiltered, Filtered, and Config-Only)",
                         "Verify that the O-RU exposes operational and configuration data via NETCONF and that the O-RU Controller retrieves and exposes this data using RESTCONF in JSON format.",
                         controller=controller)
        self.tc_model.status = models.TestStatus.conditionally_mandatory

    def run(self) -> models.TestCase:
        logging.info(f"Started running test case {self.number} ({self.name})")

        self.tc_model.startDate = datetime.now(UTC)

        test_note = models.TestNote(title="Test Case Description", 
                                   body="This test verifies that the O-RU supports NETCONF `get` and `get-config` operations for unfiltered and subtree-filtered retrievals, and that the O-RU Controller makes this data available via RESTCONF in JSON format.")
        self.tc_model.notes = models.TestNotes([test_note])

        metrics = []
        result_status = models.ResultType.FAIL
        try:
            # Step 1: Unfiltered Data Retrieval
            unfiltered_data = self._get_unfiltered_data()
            unfiltered_success = self._validate_unfiltered_data(unfiltered_data)

            # Step 2: Subtree-Filtered Retrieval
            filtered_data = self._get_filtered_data()
            filtered_success = self._validate_filtered_data(filtered_data)

            # Step 3: Configuration-Only Retrieval
            config_only_data = self._get_config_only_data()
            config_only_success = self._validate_config_only_data(config_only_data)

            # Determine overall result
            result_status = models.ResultType.PASS if (unfiltered_success and filtered_success and config_only_success) else models.ResultType.FAIL

            # Create metrics for each step
            metrics.append(self._create_data_retrieval_metric("Unfiltered Data Retrieval", 
                                                             unfiltered_data, 
                                                             unfiltered_success))
            metrics.append(self._create_data_retrieval_metric("Subtree-Filtered Data Retrieval", 
                                                             filtered_data, 
                                                             filtered_success))
            metrics.append(self._create_data_retrieval_metric("Configuration-Only Data Retrieval", 
                                                             config_only_data, 
                                                             config_only_success))

        except ReadTimeout:
            logging.error("Test case failed due to connection timeout to the controller.")
            metrics.append(self._create_timeout_error_metric())
        except Exception as e:
            logging.error(f"Test case failed due to unknown error: {str(e)}")
            metrics.append(self._create_generic_error_metric(str(e)))

        self.tc_model.result = result_status
        self.tc_model.metrics = metrics
        self.tc_model.stopDate = datetime.now(UTC)
        logging.info(f"Finished running test case {self.number} ({self.name}) with status {result_status}")

        return self.get_test_case_model()

    def _get_unfiltered_data(self) -> Dict[str, Any]:
        """
        Send a RESTCONF request without any filter to retrieve the full available data tree.

        Returns:
            Dict[str, Any]: The JSON response from the RESTCONF request.
        """
        # Get the mountpoint name from configuration
        config = get_config().get_config()
        mountpoint_name = getattr(config.test_cases, "dut_mountpoint_name", config.test_cases.tc_002_mountpoint_name)

        # Construct the URL for unfiltered data retrieval
        url = f"{self.controller.base_url}/rests/data/network-topology:network-topology/topology=topology-netconf/node={mountpoint_name}/yang-ext:mount/"

        # Make the request
        status_code, data = self._make_restconf_request(url)

        return {
            "status_code": status_code,
            "data": data,
            "mountpoint_name": mountpoint_name
        }

    def _validate_unfiltered_data(self, response: Dict[str, Any]) -> bool:
        """
        Validate the unfiltered data response.

        Args:
            response: The response from the unfiltered data retrieval.

        Returns:
            bool: True if the response is valid, False otherwise.
        """
        # Check if the status code is 200 (OK) or 413 (Request Entity Too Large)
        # 413 is acceptable for unfiltered data retrieval if the data is too large
        if response["status_code"] == 200:
            # Check if the response contains data for 200 OK response
            if not response["data"]:
                logging.error("Unfiltered data retrieval returned empty data")
                return False
        elif response["status_code"] == 413:
            # 413 Request Entity Too Large is acceptable for unfiltered data
            logging.info("Unfiltered data retrieval returned 'too-big' error (HTTP 413), which is acceptable")
            return True
        else:
            # Any other status code is an error
            logging.error(f"Unfiltered data retrieval failed with status code {response['status_code']}")
            return False

        # Additional validation could be added here

        return True

    def _get_filtered_data(self) -> Dict[str, Any]:
        """
        Send a RESTCONF request using a subtree filter to target a specific portion of the data.

        Returns:
            Dict[str, Any]: The JSON response from the RESTCONF request.
        """
        # Get the filter path and mountpoint name from configuration
        config = get_config().get_config()
        filter_path = getattr(config.test_cases, "tc_002_filter_path", "network-topology:network-topology/topology=topology-netconf")
        mountpoint_name = getattr(config.test_cases, "dut_mountpoint_name", config.test_cases.tc_002_mountpoint_name)

        # Construct the URL for filtered data retrieval
        url = f"{self.controller.base_url}/rests/data/network-topology:network-topology/topology=topology-netconf/node={mountpoint_name}/yang-ext:mount/{filter_path}"

        # Make the request
        status_code, data = self._make_restconf_request(url)

        return {
            "status_code": status_code,
            "data": data,
            "filter_path": filter_path,
            "mountpoint_name": mountpoint_name
        }

    def _validate_filtered_data(self, response: Dict[str, Any]) -> bool:
        """
        Validate the filtered data response.

        Args:
            response: The response from the filtered data retrieval.

        Returns:
            bool: True if the response is valid, False otherwise.
        """
        # Check if the status code is 200
        if response["status_code"] != 200:
            logging.error(f"Filtered data retrieval failed with status code {response['status_code']}")
            return False

        # Check if the response contains data
        if not response["data"]:
            logging.error("Filtered data retrieval returned empty data")
            return False

        # Additional validation could be added here

        return True

    def _get_config_only_data(self) -> Dict[str, Any]:
        """
        Send a RESTCONF request to retrieve only the configuration data.

        Returns:
            Dict[str, Any]: The JSON response from the RESTCONF request.
        """
        # Get the config-only path and mountpoint name from configuration
        config = get_config().get_config()
        config_path = getattr(config.test_cases, "tc_002_config_path", "network-topology:network-topology/topology=topology-netconf")
        mountpoint_name = getattr(config.test_cases, "dut_mountpoint_name", config.test_cases.tc_002_mountpoint_name)

        # Construct the URL for config-only data retrieval
        url = f"{self.controller.base_url}/rests/data/network-topology:network-topology/topology=topology-netconf/node={mountpoint_name}/yang-ext:mount/{config_path}?content=config"

        # Make the request
        status_code, data = self._make_restconf_request(url)

        return {
            "status_code": status_code,
            "data": data,
            "config_path": config_path,
            "mountpoint_name": mountpoint_name
        }

    def _validate_config_only_data(self, response: Dict[str, Any]) -> bool:
        """
        Validate the config-only data response.

        Args:
            response: The response from the config-only data retrieval.

        Returns:
            bool: True if the response is valid, False otherwise.
        """
        # Check if the status code is 200
        if response["status_code"] != 200:
            logging.error(f"Config-only data retrieval failed with status code {response['status_code']}")
            return False

        # Check if the response contains data
        if not response["data"]:
            logging.error("Config-only data retrieval returned empty data")
            return False

        # Additional validation could be added here

        return True

    def _make_restconf_request(self, url: str) -> tuple[int, Dict[str, Any]]:
        """
        Make a RESTCONF request to the given URL.

        Args:
            url: The URL to make the request to.

        Returns:
            tuple[int, Dict[str, Any]]: A tuple containing the status code and the JSON data.
        """
        try:
            # Use the controller's _fetch_data method to make the request
            status_code, data = self.controller._fetch_data(url)
            return status_code, data
        except Exception as e:
            logging.error(f"Error making RESTCONF request to {url}: {str(e)}")
            raise

    def _create_data_retrieval_metric(self, description: str, data: Dict[str, Any], success: bool) -> models.Metric:
        """
        Create a metric for a data retrieval step.

        Args:
            description: The description of the metric.
            data: The data retrieved.
            success: Whether the retrieval was successful.

        Returns:
            models.Metric: The created metric.
        """

        # Create measurements
        measurements = [
            models.Measurement(
                name="Status Code",
                values=[str(data.get("status_code", "N/A"))],
                units=models.Units.text
            )
        ]

        # Add mountpoint name measurement if available
        if "mountpoint_name" in data:
            measurements.append(
                models.Measurement(
                    name="Mountpoint Name",
                    values=[data["mountpoint_name"]],
                    units=models.Units.text
                )
            )

        # Add additional measurements if available
        if "filter_path" in data:
            measurements.append(
                models.Measurement(
                    name="Filter Path",
                    values=[data["filter_path"]],
                    units=models.Units.text
                )
            )
        if "config_path" in data:
            measurements.append(
                models.Measurement(
                    name="Config Path",
                    values=[data["config_path"]],
                    units=models.Units.text
                )
            )

        return models.Metric(
            description=description,
            measurements=models.Measurements(measurements),
            status=models.TestStatus.optional,
            result=models.ResultType.PASS if success else models.ResultType.FAIL
        )

    def _create_timeout_error_metric(self) -> models.Metric:
        """
        Create a metric for a timeout error.

        Returns:
            models.Metric: The created metric.
        """
        return models.Metric(
            description="Failed to query RESTCONF data from controller",
            measurements=models.Measurements([
                models.Measurement(name="Error", values=[self.ERROR_TIMEOUT], units=models.Units.text)
            ]),
            status=models.TestStatus.optional,
            result=models.ResultType.FAIL
        )

    def _create_generic_error_metric(self, exception_string: str) -> models.Metric:
        """
        Create a metric for a generic error.

        Args:
            exception_string: The exception message.

        Returns:
            models.Metric: The created metric.
        """
        return models.Metric(
            description="Failed to query RESTCONF data from controller",
            measurements=models.Measurements([
                models.Measurement(name="Error", values=[exception_string], units=models.Units.text)
            ]),
            status=models.TestStatus.optional,
            result=models.ResultType.FAIL
        )
