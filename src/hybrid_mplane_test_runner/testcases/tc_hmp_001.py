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

from typing import Iterable

from hybrid_mplane_test_runner.testcases.base import HybridMPlaneTestCase
from hybrid_mplane_test_runner.oru_controller.base import ORUController
import hybrid_mplane_test_runner.models.testresult_models as models
from requests.exceptions import ReadTimeout
import logging
from datetime import datetime, UTC
from hybrid_mplane_test_runner.config import get_config


class TestCase_001(HybridMPlaneTestCase):
    """
    Manages the execution of Test Case 001.

    This class represents a specific test case that aims to ensure proper transport
    and handshake functionality in an IPv4/TLS environment. It performs checks on
    NETCONF connections established between a controller and connected nodes and validates
    parameters such as connection state, node identity, and TLS/IPv4 configurations.
    Metrics are generated based on these observations for reporting purposes.

    :ivar tc_model: A representation of the test case model holding details such as notes,
        start date, stop date, result, and metrics.
    :type tc_model: models.TestCase
    :ivar number: Identifier for the test case, in this specific case "001".
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
    categories = ["basic", "connectivity", "transport"]
    suite = "Basic Connectivity"
    ERROR_TIMEOUT = "Connection to controller timed out"

    def __init__(self, controller: ORUController = None):
        super().__init__("001",
                         "Transport and Handshake in IPv4/TLS Environment",
                         "Runs basic scenario",
                         controller=controller)
        self.tc_model.status = models.TestStatus.conditionally_mandatory

    def run(self) -> models.TestCase:
        # Get expected values from configuration
        config = get_config().get_config()
        expected_name = config.test_cases.dut_mountpoint_name
        expected_status = config.test_cases.tc_001_expected_status
        expected_capabily = config.test_cases.tc_001_expected_capability
        logging.info(f"Started running test case {self.number} ({self.name})")

        self.tc_model.startDate = datetime.now(UTC)

        test_note = models.TestNote(title="Note 1", body="Just a sample test note here.")
        self.tc_model.notes = models.TestNotes([test_note])

        metrics = []
        result_status = models.ResultType.FAIL
        try:
            previous_ids = set(self.controller.initial_connections)
            logging.debug(f"Previous connections: {previous_ids}")

            current_connections = self.controller.get_netconf_connections()
            current_ids = {n.node_id for n in current_connections}
            logging.debug(f"Current connections: {current_ids}")


            new_ids = current_ids - previous_ids
            logging.debug(f"New connections: {new_ids}")
            new_connections = [n for n in current_connections if n.node_id in new_ids]
            logging.debug(f"New NetconfNode objects: {new_connections}")
            # result_status = models.ResultType.PASS if new_connections else models.ResultType.FAIL
            if new_connections:
                # Step 1: Validate general connection properties (state and node ID)
                valid_connections = [
                    conn for conn in new_connections
                    if conn.is_valid(expected_name, expected_status, expected_capabily)
                ]

                if valid_connections:
                    # Step 2: Further validate those that passed the first check for TLS and IPv4
                    logging.debug(f"Valid connections (: {valid_connections}")
                    tls_ipv4_connections = [
                        conn for conn in valid_connections
                        if self.controller.is_tls_ipv4(conn.node_id)
                    ]

                    # Determine the test result based on the TLS/IPv4 verification
                    result_status = models.ResultType.PASS if tls_ipv4_connections else models.ResultType.FAIL


            metrics.append(self._create_connection_change_metrics(previous_ids,
                                                                  current_connections,
                                                                  new_connections,
                                                                  result_status))
        except ReadTimeout:
            logging.error("Test case failed due to connection timeout to the controller.")
            metrics.append(self._create_timeout_error_metric())
        except Exception as e:
            logging.error("Test case failed due to unknown error.")
            metrics.append(self._create_generic_error_metric(str(e) + "\n" + str(e.__traceback__)))

        self.tc_model.result = result_status
        self.tc_model.metrics = metrics
        self.tc_model.stopDate = datetime.now(UTC)
        logging.info(f"Finished running test case {self.number} ({self.name}) with status {result_status}")

        return self.get_test_case_model()

    @staticmethod
    def _create_connection_change_metrics(previous_connections, current_connections, new_connections,
                                          result_status):
        def _build_measurement(name: str, connections: Iterable[str], default_message: str) -> models.Measurement:
            return models.Measurement(
                name=name,
                values = sorted([c.summary() for c in connections], key=lambda x: x["node_id"]) if connections else [default_message],
                units=models.Units.text
            )

        measurements = [
            _build_measurement("Connections Before", previous_connections, "No connections"),
            _build_measurement("Connections After", current_connections, "No connections"),
            _build_measurement("New Connections", new_connections, "No new connections observed"),
        ]

        return models.Metric(
            description="NETCONF connection change observed",
            measurements=models.Measurements(measurements),
            status=models.TestStatus.optional,
            result=result_status
        )

    def _create_timeout_error_metric(self):
        return models.Metric(
            description="Failed to query NETCONF topology from controller",
            measurements=models.Measurements([
                models.Measurement(name="Error", values=[self.ERROR_TIMEOUT], units=models.Units.text)
            ]),
            status=models.TestStatus.optional,
            result=models.ResultType.FAIL
        )

    @staticmethod
    def _create_generic_error_metric(exception_string: str):
        return models.Metric(
            description="Failed to query NETCONF topology from controller",
            measurements=models.Measurements([
                models.Measurement(name="Error", values=[exception_string], units=models.Units.text)
            ]),
            status=models.TestStatus.optional,
            result=models.ResultType.FAIL
        )
