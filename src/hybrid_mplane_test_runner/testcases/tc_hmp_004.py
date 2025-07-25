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

from typing import Dict, Any
import json
import logging
import requests
from datetime import datetime, UTC

from hybrid_mplane_test_runner.testcases.base import HybridMPlaneTestCase
from hybrid_mplane_test_runner.oru_controller.base import ORUController
import hybrid_mplane_test_runner.models.testresult_models as models
from requests.exceptions import ReadTimeout
from hybrid_mplane_test_runner.config import get_config
from hybrid_mplane_test_runner.errors import (
    HybridMPlaneError, ControllerError, NetworkError, TimeoutError, ValidationError,
    handle_error, with_error_handling
)


class TestCase_004(HybridMPlaneTestCase):
    """
    Manages the execution of Test Case 004.

    This class represents a test case that verifies the O-RU accepts valid configuration
    and that the O-RU Controller applies it via RESTCONF. It performs the following steps:
    1. Prepare a valid RESTCONF PUT request payload for o-ran-operations:operational-info
    2. Apply the configuration via RESTCONF
    3. Validate the configuration was applied correctly
    4. Optionally check for a netconf-config-change notification

    :ivar tc_model: A representation of the test case model holding details such as notes,
        start date, stop date, result, and metrics.
    :type tc_model: models.TestCase
    :ivar number: Identifier for the test case, in this specific case "004".
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
    categories = ["configuration", "operational-info", "restconf"]
    suite = "O-RU Configuration"
    ERROR_TIMEOUT = "Connection to controller timed out"
    CONFIG_KEY = "o-ran-operations:operational-info"
    RE_CALL_HOME_TIMER = "re-call-home-no-ssh-timer"
    MAX_CALL_HOME_ATTEMPTS = "max-call-home-attempts"
    EXPECTED_TIMER_VALUE = 90
    EXPECTED_ATTEMPTS_VALUE = 10

    def __init__(self, controller: ORUController = None):
        super().__init__("004",
                         "O-RU Configurability Test (Positive Case)",
                         "Verify that the O-RU accepts valid operational-info configuration and that the O-RU Controller applies it via RESTCONF.",
                         controller=controller)
        self.tc_model.status = models.TestStatus.conditionally_mandatory

    def run(self) -> models.TestCase:
        logging.info(f"Started running test case {self.number} ({self.name})")

        self.tc_model.startDate = datetime.now(UTC)

        test_note = models.TestNote(title="Test Case Description", 
                                   body="This test verifies that the O-RU accepts valid configuration for operational-info and that the configuration can be successfully applied through the O-RU Controller using RESTCONF.")
        self.tc_model.notes = models.TestNotes([test_note])

        metrics = []
        result_status = models.ResultType.FAIL
        try:
            # Step 1: Prepare Configuration Payload
            config_payload = self._prepare_config_payload()

            # Step 2: Apply Configuration
            apply_result = self._apply_configuration(config_payload)
            apply_success = self._validate_apply_result(apply_result)

            # Step 3: Validate Configuration
            validation_result = self._validate_configuration()
            validation_success = self._validate_validation_result(validation_result)

            # Step 4 (Optional): Check for Configuration Change Notification
            notification_result = self._check_for_notification()
            notification_success = self._validate_notification_result(notification_result)

            # Determine overall result
            # Note: notification check is optional, so we don't include it in the overall result
            result_status = models.ResultType.PASS if (apply_success and validation_success) else models.ResultType.FAIL

            # Create metrics for each step
            metrics.append(self._create_config_payload_metric("Configuration Payload", 
                                                             config_payload))
            metrics.append(self._create_apply_config_metric("Apply Configuration", 
                                                          apply_result, 
                                                          apply_success))
            metrics.append(self._create_validation_metric("Validate Configuration", 
                                                        validation_result, 
                                                        validation_success))
            if notification_result:
                metrics.append(self._create_notification_metric("Configuration Change Notification", 
                                                              notification_result, 
                                                              notification_success))

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

    def _prepare_config_payload(self) -> Dict[str, Any]:
        """
        Prepare a valid RESTCONF PUT request payload for o-ran-operations:operational-info.

        Returns:
            Dict[str, Any]: The configuration payload.
        """
        # Get configuration values from config
        config = get_config().get_config()
        mountpoint_name = getattr(config.test_cases, "tc_004_mountpoint_name", "pynts-o-ru-hybrid")

        # Construct a valid payload for operational-info
        # This is a simplified example - in a real implementation, this would be more complex
        # and would use actual values from the configuration
        payload = {
            "o-ran-operations:operational-info": {
                "re-call-home-no-ssh-timer": self.EXPECTED_TIMER_VALUE,
                "max-call-home-attempts": self.EXPECTED_ATTEMPTS_VALUE
            }
        }

        return {
            "payload": payload,
            "mountpoint_name": mountpoint_name
        }

    def _apply_configuration(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply the configuration to the O-RU via RESTCONF.

        Args:
            config_data: The configuration data to apply.

        Returns:
            Dict[str, Any]: The result of applying the configuration.
        """
        mountpoint_name = config_data["mountpoint_name"]
        payload = config_data["payload"]

        # Construct the URL for the configuration
        url = f"{self.controller.base_url}/rests/data/network-topology:network-topology/topology=topology-netconf/node={mountpoint_name}/yang-ext:mount/o-ran-operations:operational-info"

        # Make the PUT request
        status_code, response_data = self._make_restconf_put_request(url, payload)

        return {
            "status_code": status_code,
            "response_data": response_data,
            "url": url,
            "payload": payload
        }

    def _validate_apply_result(self, apply_result: Dict[str, Any]) -> bool:
        """
        Validate the result of applying the configuration.

        Args:
            apply_result: The result of applying the configuration.

        Returns:
            bool: True if the configuration was applied successfully, False otherwise.
        """
        # Check if the status code indicates success (200 OK or 204 No Content)
        if apply_result["status_code"] in [200, 204]:
            logging.info("Configuration applied successfully")
            return True
        else:
            logging.error(f"Failed to apply configuration: status code {apply_result['status_code']}")
            return False

    def _validate_configuration(self) -> Dict[str, Any]:
        """
        Validate that the configuration was applied correctly by retrieving it via RESTCONF.

        Returns:
            Dict[str, Any]: The result of validating the configuration.
        """
        # Get configuration values from config
        config = get_config().get_config()
        mountpoint_name = getattr(config.test_cases, "tc_004_mountpoint_name", "pynts-o-ru-hybrid")

        # Construct the URL for retrieving the configuration
        url = f"{self.controller.base_url}/rests/data/network-topology:network-topology/topology=topology-netconf/node={mountpoint_name}/yang-ext:mount/o-ran-operations:operational-info"

        # Make the GET request
        status_code, data = self._make_restconf_request(url)

        return {
            "status_code": status_code,
            "data": data,
            "url": url,
            "mountpoint_name": mountpoint_name
        }

    def _validate_validation_result(self, validation_result: Dict[str, Any]) -> bool:
        """
        Validate the result of validating the configuration.

        Args:
            validation_result: The result of validating the configuration.

        Returns:
            bool: True if the validation was successful, False otherwise.
        """

        def _check_key_value(data: Dict[str, Any], key: str, expected_value: str = None) -> bool:
            if key not in data:
                logging.error(f"Missing key '{key}' in configuration data.")
                return False
            if expected_value and data[key] != expected_value:
                logging.error(f"Key '{key}' has an unexpected value: {data[key]} (expected: {expected_value}).")
                return False
            return True

        # Validate status code
        if validation_result.get("status_code") != 200:
            logging.error(f"Failed to retrieve configuration: status code {validation_result.get('status_code')}")
            return False

        data = validation_result.get("data")
        if not data:
            logging.error("Configuration retrieval returned empty data.")
            return False

        # Validate configuration keys and their values
        operational_info = data.get(self.CONFIG_KEY)
        if not operational_info:
            logging.error(f"Missing '{self.CONFIG_KEY}' in configuration data.")
            return False

        if not _check_key_value(operational_info, self.RE_CALL_HOME_TIMER, self.EXPECTED_TIMER_VALUE):
            return False

        if not _check_key_value(operational_info, self.MAX_CALL_HOME_ATTEMPTS, self.EXPECTED_ATTEMPTS_VALUE):
            return False

        logging.info("Configuration validation successful")
        return True

    def _check_for_notification(self) -> Dict[str, Any]:
        """
        Check for a netconf-config-change notification.

        Returns:
            Dict[str, Any]: The result of checking for a notification, or None if notifications are not supported.
        """
        # This is an optional step, so we'll just return None for now
        # In a real implementation, this would check for notifications
        return None

    def _validate_notification_result(self, notification_result: Dict[str, Any]) -> bool:
        """
        Validate the result of checking for a notification.

        Args:
            notification_result: The result of checking for a notification.

        Returns:
            bool: True if the notification check was successful, False otherwise.
        """
        # This is an optional step, so we'll just return True if notification_result is None
        if notification_result is None:
            return True

        # In a real implementation, this would validate the notification
        return True

    def _make_restconf_request(self, url: str) -> tuple[int, Dict[str, Any]]:
        """
        Make a RESTCONF GET request to the given URL.

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

    def _make_restconf_put_request(self, url: str, payload: Dict[str, Any]) -> tuple[int, Dict[str, Any]]:
        """
        Make a RESTCONF PUT request to the given URL with the given payload.

        Args:
            url: The URL to make the request to.
            payload: The payload to send with the request.

        Returns:
            tuple[int, Dict[str, Any]]: A tuple containing the status code and the JSON data.
        """
        try:
            logging.info(f"Making RESTCONF PUT request to {url} with payload: {payload}")
            headers = {
                "Content-Type": "application/yang-data+json",
                "Accept": "application/yang-data+json"
            }
            response = requests.put(
                url,
                auth=(self.controller.username, self.controller.password),
                headers=headers,
                json=payload,
                verify=False,
                timeout=self.controller.timeout
            )
            status_code = response.status_code
            response_data = response.json() if status_code == 200 else {}

            if status_code not in [200, 204]:
                logging.error(f"RESTCONF PUT request failed with status code {status_code}")
                logging.error(f"Response: {response.text}")

            return status_code, response_data
        except Exception as e:
            logging.error(f"Error making RESTCONF PUT request to {url}: {str(e)}")
            raise

    def _create_config_payload_metric(self, description: str, config_data: Dict[str, Any]) -> models.Metric:
        """
        Create a metric for the configuration payload.

        Args:
            description: The description of the metric.
            config_data: The configuration data.

        Returns:
            models.Metric: The created metric.
        """
        measurements = [
            models.Measurement(
                name="Configuration Payload",
                values=[json.dumps(config_data["payload"], indent=2)],
                units=models.Units.text
            )
        ]

        if "mountpoint_name" in config_data:
            measurements.append(
                models.Measurement(
                    name="Mountpoint Name",
                    values=[config_data["mountpoint_name"]],
                    units=models.Units.text
                )
            )

        return models.Metric(
            description=description,
            measurements=models.Measurements(measurements),
            status=models.TestStatus.optional,
            result=models.ResultType.PASS
        )

    def _create_apply_config_metric(self, description: str, apply_result: Dict[str, Any], success: bool) -> models.Metric:
        """
        Create a metric for applying the configuration.

        Args:
            description: The description of the metric.
            apply_result: The result of applying the configuration.
            success: Whether the application was successful.

        Returns:
            models.Metric: The created metric.
        """
        measurements = [
            models.Measurement(
                name="Status Code",
                values=[str(apply_result.get("status_code", "N/A"))],
                units=models.Units.text
            ),
            models.Measurement(
                name="URL",
                values=[apply_result.get("url", "N/A")],
                units=models.Units.text
            )
        ]

        return models.Metric(
            description=description,
            measurements=models.Measurements(measurements),
            status=models.TestStatus.optional,
            result=models.ResultType.PASS if success else models.ResultType.FAIL
        )

    def _create_validation_metric(self, description: str, validation_result: Dict[str, Any], success: bool) -> models.Metric:
        """
        Create a metric for validating the configuration.

        Args:
            description: The description of the metric.
            validation_result: The result of validating the configuration.
            success: Whether the validation was successful.

        Returns:
            models.Metric: The created metric.
        """
        measurements = [
            models.Measurement(
                name="Status Code",
                values=[str(validation_result.get("status_code", "N/A"))],
                units=models.Units.text
            ),
            models.Measurement(
                name="URL",
                values=[validation_result.get("url", "N/A")],
                units=models.Units.text
            )
        ]

        if "data" in validation_result and validation_result["data"]:
            measurements.append(
                models.Measurement(
                    name="Retrieved Configuration",
                    values=[json.dumps(validation_result["data"], indent=2)],
                    units=models.Units.text
                )
            )

        return models.Metric(
            description=description,
            measurements=models.Measurements(measurements),
            status=models.TestStatus.optional,
            result=models.ResultType.PASS if success else models.ResultType.FAIL
        )

    def _create_notification_metric(self, description: str, notification_result: Dict[str, Any], success: bool) -> models.Metric:
        """
        Create a metric for checking for a notification.

        Args:
            description: The description of the metric.
            notification_result: The result of checking for a notification.
            success: Whether the notification check was successful.

        Returns:
            models.Metric: The created metric.
        """
        measurements = [
            models.Measurement(
                name="Notification Present",
                values=["Yes" if notification_result else "No"],
                units=models.Units.text
            )
        ]

        if notification_result and "timestamp" in notification_result:
            measurements.append(
                models.Measurement(
                    name="Notification Timestamp",
                    values=[notification_result["timestamp"]],
                    units=models.Units.text
                )
            )

        if notification_result and "data_path" in notification_result:
            measurements.append(
                models.Measurement(
                    name="Notification Data Path",
                    values=[notification_result["data_path"]],
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
            description="Failed to communicate with controller",
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
            description="Failed to execute test case",
            measurements=models.Measurements([
                models.Measurement(name="Error", values=[exception_string], units=models.Units.text)
            ]),
            status=models.TestStatus.optional,
            result=models.ResultType.FAIL
        )
