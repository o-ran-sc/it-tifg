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
from datetime import datetime, UTC

from hybrid_mplane_test_runner.testcases.base import HybridMPlaneTestCase
from hybrid_mplane_test_runner.oru_controller.base import ORUController
import hybrid_mplane_test_runner.models.testresult_models as models
from requests.exceptions import ReadTimeout
from hybrid_mplane_test_runner.config import get_config


class TestCase_003(HybridMPlaneTestCase):
    """
    Manages the execution of Test Case 003.

    This class represents a test case that verifies the O-RU has at least two active NETCONF sessions
    (one towards the O-RU Controller and another towards the O-DU) by checking the ietf-netconf-monitoring
    YANG model exposed by the O-RU.

    :ivar tc_model: A representation of the test case model holding details such as notes,
        start date, stop date, result, and metrics.
    :type tc_model: models.TestCase
    :ivar number: Identifier for the test case, in this specific case "003".
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
    categories = ["basic", "netconf", "sessions"]
    suite = "NETCONF Sessions"
    ERROR_TIMEOUT = "Connection to controller timed out"

    def __init__(self, controller: ORUController = None):
        super().__init__("003",
                         "NETCONF Sessions Verification",
                         "Verify that the O-RU has at least two active NETCONF sessions (one towards the O-RU Controller and another towards the O-DU).",
                         controller=controller)
        self.tc_model.status = models.TestStatus.conditionally_mandatory

    def run(self) -> models.TestCase:
        logging.info(f"Started running test case {self.number} ({self.name})")

        self.tc_model.startDate = datetime.now(UTC)

        test_note = models.TestNote(title="Test Case Description", 
                                   body="This test verifies that the O-RU has at least two active NETCONF sessions by checking the ietf-netconf-monitoring YANG model exposed by the O-RU.")
        self.tc_model.notes = models.TestNotes([test_note])

        metrics = []
        result_status = models.ResultType.FAIL
        try:
            # Get NETCONF sessions data
            sessions_data = self._get_netconf_sessions()
            sessions_success = self._validate_netconf_sessions(sessions_data)

            # Determine overall result
            result_status = models.ResultType.PASS if sessions_success else models.ResultType.FAIL

            # Create metrics for the test
            metrics.append(self._create_sessions_metric("NETCONF Sessions Verification", 
                                                       sessions_data, 
                                                       sessions_success))

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

    def _get_netconf_sessions(self) -> Dict[str, Any]:
        """
        Send a RESTCONF request to retrieve the NETCONF sessions information.

        Returns:
            Dict[str, Any]: The JSON response from the RESTCONF request.
        """
        # Get the mountpoint name from configuration
        config = get_config().get_config()
        mountpoint_name = config.test_cases.dut_mountpoint_name

        # Construct the URL for NETCONF sessions retrieval
        url = f"{self.controller.base_url}/rests/data/network-topology:network-topology/topology=topology-netconf/node={mountpoint_name}/yang-ext:mount/ietf-netconf-monitoring:netconf-state/sessions?content=nonconfig"

        # Make the request
        status_code, data = self._make_restconf_request(url)

        return {
            "status_code": status_code,
            "data": data,
            "mountpoint_name": mountpoint_name
        }

    def _validate_netconf_sessions(self, response: Dict[str, Any]) -> bool:
        """
        Validate the NETCONF sessions response.

        Args:
            response: The response from the NETCONF sessions retrieval.

        Returns:
            bool: True if the response is valid and contains at least two sessions, False otherwise.
        """
        # Check if the status code is 200
        if response["status_code"] != 200:
            logging.error(f"NETCONF sessions retrieval failed with status code {response['status_code']}")
            return False

        # Check if the response contains data
        if not response["data"]:
            logging.error("NETCONF sessions retrieval returned empty data")
            return False

        # Check if the response contains the sessions data
        if "ietf-netconf-monitoring:sessions" not in response["data"]:
            logging.error("NETCONF sessions data not found in response")
            return False

        # Check if the sessions list exists
        sessions_data = response["data"]["ietf-netconf-monitoring:sessions"]
        if "session" not in sessions_data:
            logging.error("Sessions list not found in response")
            return False

        # Check if there are at least two sessions
        sessions = sessions_data["session"]
        if len(sessions) < 2:
            logging.error(f"Expected at least 2 NETCONF sessions, but found {len(sessions)}")
            return False

        logging.info(f"Found {len(sessions)} NETCONF sessions, which meets the requirement of at least 2 sessions")
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

    def _create_sessions_metric(self, description: str, data: Dict[str, Any], success: bool) -> models.Metric:
        """
        Create a metric for the NETCONF sessions verification.

        Args:
            description: The description of the metric.
            data: The data retrieved.
            success: Whether the verification was successful.

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

        # Add session count if available
        if "data" in data and "ietf-netconf-monitoring:sessions" in data["data"] and "session" in data["data"]["ietf-netconf-monitoring:sessions"]:
            sessions = data["data"]["ietf-netconf-monitoring:sessions"]["session"]
            measurements.append(
                models.Measurement(
                    name="Session Count",
                    values=[str(len(sessions))],
                    units=models.Units.text
                )
            )

            # Add session details
            for i, session in enumerate(sessions):
                session_id = session.get("session-id", "N/A")
                username = session.get("username", "N/A")
                source_host = session.get("source-host", "N/A")
                transport = session.get("transport", "N/A")

                measurements.append(
                    models.Measurement(
                        name=f"Session {i+1} Details",
                        values=[f"ID: {session_id}, User: {username}, Host: {source_host}, Transport: {transport}"],
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
