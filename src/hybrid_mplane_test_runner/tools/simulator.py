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
import subprocess
import time

class MPInterfaceSimulator:
    """
    MPInterfaceSimulator manages the lifecycle and operations of a simulator service.

    Provides functionalities to start, stop, collect logs, and check the readiness of
    a simulator service running in a Docker Compose environment. It relies on environment
    variables to configure its behavior, such as the path to the Docker Compose file,
    the service name, and the waiting time for the simulator to become ready.

    :ivar compose_file: Path to the Docker Compose file used to manage the simulator.
    :type compose_file: str
    :ivar service_name: Name of the simulator service managed by this class.
    :type service_name: str
    :ivar wait_time: Number of seconds to wait for the simulator to become ready after starting.
    :type wait_time: int
    """
    def __init__(self):
        self.compose_file = os.getenv("SIMULATOR_COMPOSE_FILE", "tools/simulator/docker-compose.yaml")
        self.service_name = os.getenv("SIMULATOR_SERVICE_NAME", "pynts-o-ru-hybrid")
        self.wait_time = int(os.getenv("SIMULATOR_WAIT_TIME", "5"))

    def start(self):
        print(f"🚀 Starting simulator service '{self.service_name}' from '{self.compose_file}'...")
        subprocess.run([
            "docker", "compose",
            "-f", self.compose_file,
            "up", "-d", self.service_name
        ], check=True)
        print(f"⏳ Waiting {self.wait_time} seconds for simulator to become ready...")
        time.sleep(self.wait_time)

    def stop(self):
        print(f"🛑 Stopping simulator service '{self.service_name}'...")
        subprocess.run([
            "docker", "compose",
            "-f", self.compose_file,
            "down"
        ], check=False)

    def collect_logs(self, destination_path: str):
        container_path = "/var/log/pynts.log"
        print(f"📦 Collecting simulator logs from '{self.service_name}:{container_path}'...")
        try:
            subprocess.run([
                "docker", "compose",
                "-f", self.compose_file,
                "cp",
                f"{self.service_name}:{container_path}",
                destination_path
            ], check=True)
            print(f"✅ Simulator log saved to {destination_path}")
        except subprocess.CalledProcessError:
            print(f"⚠️  Failed to copy simulator log from container. It may not exist.")

    def is_ready(self):
        return True
