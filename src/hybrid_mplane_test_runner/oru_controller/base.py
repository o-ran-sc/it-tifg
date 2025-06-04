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

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class NetconfNode(ABC):
    """
    Represents an abstract base class (ABC) for a NetconfNode.

    Defines the minimal interface and attributes required for a network configuration
    node to be managed effectively. Implementations of this abstract class must provide
    details on creating an instance from raw data and validating its properties
    against expected values.

    This class facilitates handling of nodes in a standardized manner, ensuring
    consistency in node representation and management throughout the system.

    :ivar node_id: Unique identifier of the node.
    :type node_id: str
    :ivar connection_status: Current connection status of the node.
    :type connection_status: str
    :ivar host: Hostname or IP address of the node.
    :type host: str
    :ivar port: Port number used to communicate with the node.
    :type port: str
    :ivar available_capabilities: The capabilities the node supports represented by a dictionary.
    :type available_capabilities: dict
    """
    node_id: str
    connection_status: str
    host: str
    port: str
    available_capabilities: dict

    def __repr__(self):
        # Build a dictionary of fields excluding available_capabilities
        fields_to_show = {
            k: v
            for k, v in self.__dict__.items()
            if k != "available_capabilities"
        }
        field_repr = ", ".join(f"{k}={v!r}" for k, v in fields_to_show.items())
        return f"{self.__class__.__name__}({field_repr})"

    def __str__(self):
        return self.__repr__()

    def summary(self):
        return {
            "node_id": self.node_id,
            "connection_status": self.connection_status,
            "host": self.host,
            "port": self.port
        }

    def __hash__(self):
        """
        Make the class hashable by excluding mutable fields like 'available_capabilities'.
        """
        return hash((self.node_id, self.connection_status, self.host, self.port))

    def __eq__(self, other):
        """
        Ensure equality checks are consistent with the __hash__ function.
        """
        if not isinstance(other, NetconfNode):
            return False
        return (
                self.node_id == other.node_id and
                self.connection_status == other.connection_status and
                self.host == other.host and
                self.port == other.port
        )

    @classmethod
    @abstractmethod
    def from_raw(cls, data: dict) -> "NetconfNode":
        """
        Parse and construct a NetconfNode instance from raw input data.

        :param data: A dictionary containing node information.
        :return: An instance of a subclass of NetconfNode.
        """
        pass

    @abstractmethod
    def is_valid(self, expected_name: str, expected_status: str, expected_capability: str) -> bool:
        """
        Check if the node matches the expected name and status.

        :param expected_capability: Expected capability to be present in the node (O-RU specific YANG model).
        :param expected_name: Expected node_id of the node.
        :param expected_status: Expected connection status of the node.
        :return: True if valid, False otherwise.
        """
        pass



class ORUController(ABC):
    """
    Represents an abstract base controller for O-RU management.

    This class defines the structure and base methods for interacting with O-RU Controllers.
    It handles authentication and maintains information about initial
    connections. The class serves as a blueprint for concrete implementations that manage
    NETCONF connections and verify node connectivity configurations.

    :ivar base_url: The base URL for the O-RU Controller, used for RESTCONF connections.
    :type base_url: str
    :ivar username: The username for authenticating with the O-RU Controller.
    :type username: str
    :ivar password: The password for authenticating with the O-RU Controller.
    :type password: str
    :ivar initial_connections: A list to store initial connections information for tracking purposes.
    :type initial_connections: list
    """
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.initial_connections = []

    @abstractmethod
    def get_netconf_connections(self) -> list[NetconfNode]:
        """
        Returns a list of currently known NETCONF NetconfNode instances.
        """
        pass

    @abstractmethod
    def is_tls_ipv4(self, node_id: str) -> bool:
        """
        Verify that this specific node uses CallHome TLS over IPv4.
        """
        pass
