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
from hybrid_mplane_test_runner.oru_controller.base import ORUController
import hybrid_mplane_test_runner.models.testresult_models as models

class HybridMPlaneTestCase(ABC):
    """
    Represents an abstract base class for a hybrid management plane test case.

    This class serves as a blueprint for implementing specific hybrid management plane test cases.
    It holds the basic structure and attributes required for defining a test case model and the
    associated operational controller. The class provides mechanisms to manage test case metrics
    and results. Derived classes must implement the initialization and `run` method for executing
    specific test logic.

    :ivar tc_model: The test case model containing details about the test case, such as name,
        description, status, and metrics.
    :type tc_model: models.TestCase
    :ivar controller: The operational controller responsible for managing ORU (Outdoor Radio Unit)
        for the test case.
    :type controller: ORUController
    :ivar number: The test case number used for identification.
    :type number: str
    :ivar name: The name of the test case.
    :type name: str
    :ivar description: Detailed description of the test case.
    :type description: str
    """
    tc_model: models.TestCase
    controller: ORUController
    number: str
    name: str
    description: str

    @abstractmethod
    def __init__(self, number: str, name: str, description: str, controller: ORUController):
        self.number = number
        self.name = name
        self.description = description
        metrics = [models.Metric(
            description="Generic metric",
            measurements=models.Measurements([
                models.Measurement(name="Generic measurement", values=["None"], units=models.Units.text)
            ]),
            status=models.TestStatus.optional,
            result=models.ResultType.FAIL
        )]
        self.tc_model = models.TestCase(number=number,
                                        name=name,
                                        description=description,
                                        result=models.ResultType.FAIL,
                                        status=models.TestStatus.optional,
                                        metrics=metrics)

        self.controller = controller

    def get_test_case_model(self) -> models.TestCase:
        return self.tc_model


    @abstractmethod
    def run(self) -> models.TestCase:
        """Executes the test and returns results and metrics."""
        pass
