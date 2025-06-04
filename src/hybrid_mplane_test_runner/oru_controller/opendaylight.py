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

# File: oru_controller/opendaylight.py
import os
import logging
import requests
import urllib3
from datetime import datetime, UTC
from requests.exceptions import HTTPError, Timeout
from hybrid_mplane_test_runner.oru_controller.base import ORUController, NetconfNode
from hybrid_mplane_test_runner.errors import (
    HybridMPlaneError, ControllerError, NetworkError, TimeoutError, ValidationError,
    handle_error, with_error_handling
)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class OpenDaylightNetconfNode(NetconfNode):
    """
    Represents an OpenDaylight-specific NETCONF node.

    This class extends the behavior of a base NetconfNode to include OpenDaylight-specific
    attributes and methods. It is used to parse and validate nodes based on OpenDaylight's
    NETCONF topology requirements. The class provides functionality to construct itself
    from raw data and perform specific validations regarding node connection and capabilities.

    :ivar node_id: Unique identifier for the NETCONF node.
    :type node_id: str
    :ivar connection_status: Status of the NETCONF node's connection.
    :type connection_status: str
    :ivar host: Host address of the NETCONF node.
    :type host: str or None
    :ivar port: Port number used by the NETCONF node.
    :type port: int or None
    :ivar available_capabilities: Dictionary containing capabilities available on the NETCONF node.
    :type available_capabilities: dict
    """

    @classmethod
    @with_error_handling(error_type=ValidationError, message="Failed to parse NETCONF node data")
    def from_raw(cls, data: dict) -> "OpenDaylightNetconfNode":
        """
        Parse and construct a OpenDaylightNetconfNode from raw data.

        :param data: Raw data dictionary containing node information.
        :type data: dict
        :return: A new OpenDaylightNetconfNode instance.
        :rtype: OpenDaylightNetconfNode
        :raises ValidationError: If the required node-id is missing or data is invalid.
        """
        logging.debug(f"Entering from_raw with data: {data}")
        node_id = data.get("node-id")
        if not node_id:
            raise ValidationError(
                "Missing node-id in NETCONF node data",
                context={"data": data}
            )

        connection_status = data.get("netconf-node-topology:connection-status", "unknown")
        host = data.get("netconf-node-topology:host")
        port = data.get("netconf-node-topology:port")
        available_capabilities = data.get("netconf-node-topology:available-capabilities", {})

        node = cls(
            node_id=node_id,
            connection_status=connection_status,
            host=host,
            port=port,
            available_capabilities=available_capabilities,
        )
        logging.debug(f"Constructed OpenDaylightNetconfNode: {node}")
        return node

    def is_valid(self, expected_name: str, expected_status: str, required_capability: str) -> bool:
        """
        OpenDaylight-specific validation for node connection.
        This method also checks if a specific capability is available.

        :param expected_name: Expected node ID.
        :param expected_status: Expected connection status.
        :param required_capability: Capability URI to check in the available capabilities.
        :return: True if the node matches the expected ID, status, and contains the required capability, False otherwise.
        """
        has_capability = any(
            required_capability in cap.get("capability", "")
            for cap in self.available_capabilities.get("available-capability", [])
        )
        return self.node_id == expected_name and self.connection_status == expected_status and has_capability



class OpenDaylightController(ORUController):
    """
    This class manages the interaction with an OpenDaylight (ODL) controller, providing operations
    for fetching NETCONF connections, CallHome connections, and determining specific connection
    attributes like TLS over IPv4. It extends the base ORUController class.

    The purpose of the OpenDaylightController class is to abstract and facilitate communication with
    the ODL RESTCONF API, particularly for operations related to network topology and CallHome device
    management. Users can leverage this class to query and parse data from the ODL controller,
    while handling possible exceptions and recording debugging logs for troubleshooting.

    :ivar headers: Default headers used for requests to the OpenDaylight controller.
    :type headers: dict
    :ivar topology_url: URL endpoint for retrieving network topology data from the controller.
    :type topology_url: str
    :ivar callhome_devices_url: URL endpoint for retrieving CallHome device configurations.
    :type callhome_devices_url: str
    :ivar debug_entries: List of debug log entries for all requests made by the instance.
    :type debug_entries: list
    :ivar initial_connections: Initial NETCONF connections retrieved during object initialization.
    :type initial_connections: list
    """
    def __init__(self, base_url=None, username=None, password=None, timeout=10):
        base_url = base_url or os.getenv("ODL_CONTROLLER_BASE_URL", "https://odlux.oam.smo.o-ran-sc.org")
        username = username or os.getenv("ODL_CONTROLLER_USERNAME", "admin")
        password = password or os.getenv("ODL_CONTROLLER_PASSWORD", "admin")
        self.headers = {"Accept": "application/yang-data+json"}
        super().__init__(base_url, username, password)
        self.topology_url = f"{self.base_url}/rests/data/network-topology:network-topology/topology=topology-netconf"
        self.callhome_devices_url = f"{self.base_url}/rests/data/odl-netconf-callhome-server:netconf-callhome-server/allowed-devices?content=nonconfig"
        self.debug_entries = []
        self.timeout = timeout

        self.initial_connections = self.get_netconf_connections()

    @with_error_handling(error_type=ControllerError, message="Failed to fetch data from controller")
    def _fetch_data(self, url: str) -> tuple[int, dict]:
        """
        Helper method to perform a GET request and return the status code and response JSON.

        :param url: The URL to fetch data from.
        :type url: str
        :return: A tuple containing the status code and the JSON data parsed from the response,
                 or an empty dictionary if the request fails.
        :rtype: tuple[int, dict]
        :raises TimeoutError: If the request times out.
        :raises NetworkError: If there's a network-related error.
        :raises ControllerError: If there's an error with the controller response.
        """
        debug_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "url": url,
            "method": "GET",
            "headers": self.headers,
        }
        try:
            logging.info(f"Querying controller at {url}")
            response = requests.get(
                url,
                auth=(self.username, self.password),
                headers=self.headers,
                verify=False,
                timeout=self.timeout
            )
            status_code = response.status_code
            response_data = response.json() if status_code == 200 else {}

            debug_entry["status_code"] = status_code
            debug_entry["response_body"] = response_data if status_code == 200 else response.text

            if status_code == 409:
                logging.warning(f"Received 409 Conflict from {url} — assuming no data available.")
                return status_code, {}

            response.raise_for_status()
            return status_code, response_data

        except Timeout as e:
            debug_entry["error"] = "Timeout"
            raise TimeoutError(
                f"Request to {url} timed out after {self.timeout} seconds",
                context={
                    "url": url,
                    "timeout": self.timeout,
                    "headers": self.headers
                },
                cause=e
            )
        except HTTPError as e:
            debug_entry["error"] = str(e)
            raise NetworkError(
                f"HTTP error when querying {url}: {e.response.status_code} {e.response.reason}",
                context={
                    "url": url,
                    "status_code": e.response.status_code,
                    "reason": e.response.reason,
                    "response_text": e.response.text[:500]  # Include first 500 chars of response
                },
                cause=e
            )
        except Exception as e:
            debug_entry["error"] = str(e)
            raise ControllerError(
                f"Unexpected error while querying {url}",
                context={
                    "url": url,
                    "error_type": type(e).__name__,
                    "error_details": str(e)
                },
                cause=e
            )
        finally:
            self.debug_entries.append(debug_entry)

    @with_error_handling(error_type=ControllerError, message="Failed to get NETCONF connections")
    def get_netconf_connections(self) -> list:
        """
        Fetch the NETCONF connections by parsing the network topology data from the controller.

        :return: A list of OpenDaylightNetconfNode instances.
        :rtype: list
        :raises ControllerError: If there's an error fetching or parsing the connections.
        """
        logging.debug("Entering get_netconf_connections")
        status_code, data = self._fetch_data(self.topology_url)
        if status_code == 409:
            logging.warning("Received 409 Conflict — assuming no NETCONF connections yet.")
            return []

        topology = data.get("network-topology:topology", [])
        if not topology:
            logging.info("Topology data is empty; returning empty connections list.")
            logging.debug("Exiting get_netconf_connections with an empty list")
            return []

        nodes = topology[0].get("node", [])
        logging.debug(f"Received nodes from topology: {nodes}")

        try:
            connections = [OpenDaylightNetconfNode.from_raw(n) for n in nodes]
            logging.debug(f"Returning NETCONF connections: {connections}")
            return connections
        except ValidationError as e:
            # Wrap the validation error with more context
            raise ControllerError(
                "Failed to parse NETCONF connections from topology data",
                context={"topology_url": self.topology_url, "node_count": len(nodes)},
                cause=e
            )

    @with_error_handling(error_type=ControllerError, message="Failed to get CallHome connections")
    def get_callhome_connections(self) -> list:
        """
        Fetch the callhome connections by parsing the allowed devices data from the controller.

        :return: A list of callhome device configurations.
        :rtype: list
        :raises ControllerError: If there's an error fetching or parsing the connections.
        """
        logging.debug("Entering get_callhome_connections")
        status_code, data = self._fetch_data(self.callhome_devices_url)
        if status_code == 409:
            logging.warning("Received 409 Conflict — assuming no callhome connections yet.")
            logging.debug("Exiting get_callhome_connections with an empty list")
            return []

        callhome_devices = data.get("odl-netconf-callhome-server:allowed-devices", {}).get("device", [])
        if not callhome_devices:
            logging.info("Callhome-server data is empty; returning empty connections list.")
            logging.debug("Exiting get_callhome_connections with an empty list")
            return []

        logging.debug(f"Received callhome devices: {callhome_devices}")
        return callhome_devices

    @with_error_handling(error_type=ControllerError, message="Failed to check TLS over IPv4 status")
    def is_tls_ipv4(self, node_id: str) -> bool:
        """
        Verify that this specific node uses CallHome TLS over IPv4.
        This is OpenDaylight-specific and assumes the `connection-status` or related fields provide details.

        :param node_id: The unique ID of the node to check.
        :type node_id: str
        :return: True if the node uses CallHome TLS over IPv4 and its status is CONNECTED, False otherwise.
        :rtype: bool
        :raises ControllerError: If there's an error checking the TLS over IPv4 status.
        """
        logging.debug(f"Entering is_tls_ipv4 with node_id: {node_id}")
        # Retrieve all CallHome connections
        callhome_devices = self.get_callhome_connections()

        # Check each device to find a match with the given node_id
        for device in callhome_devices:
            # Check the unique ID matches, status is CONNECTED, and tls-client-params is present
            if (
                    device.get("unique-id") == node_id
                    and device.get("callhome-status:device-status") == "CONNECTED"
                    and "tls-client-params" in device
            ):
                logging.debug(f"Device {node_id} uses CallHome TLS over IPv4 and is CONNECTED")
                return True

        logging.debug(f"No matching callhome device found for node_id: {node_id}")
        return False

    @with_error_handling(error_type=ControllerError, message="Failed to get debug log")
    def get_debug_log(self) -> list:
        """
        Get the debug log entries for all requests made by this controller instance.

        :return: A list of debug log entries.
        :rtype: list
        :raises ControllerError: If there's an error retrieving the debug log.
        """
        return self.debug_entries
