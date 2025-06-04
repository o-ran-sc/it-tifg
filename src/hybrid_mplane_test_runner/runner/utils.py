# Copyright 2025 highstreet technologies USA Corp., University of New Hampshire
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

"""
This module includes tools that wrap the generated models from oran_results_builder.models.

These tools intend to make building a results archive easier with tools such as:
    - Artifact Mapping
    - Archive Generation
"""

import os
from abc import ABC, abstractmethod
from hybrid_mplane_test_runner.models.testresult_models import *
from pathlib import Path
from zipfile import ZipFile


class ArchiveBuilder():
    """
    Utility class that combines generated schema datamodels with archiving functions.
    Start by initializing an ArchiveBuiler, adding artifacts, setting the TestResultsSummary, then exporting the archive.

    Usage example:

        def main():

            result: TestResultsSummary = Example1().testResultsSummary

            archive_builder = ArchiveBuilder()
            archive_builder.set_results(result)

            # Add artifacts to TestCase either before you lose the reference to the TestCase or after by programatically searching for the correct TestCase
            # TODO - Example
            tc1_log: Artifact = archive_builder.include_artifact(Path("/workspaces/results-builder/artifact1.txt"), Path("TC1"), "log.txt", "log file for TC1")
            tc2_log: Artifact = archive_builder.include_artifact(Path("/workspaces/results-builder/artifact2.txt"), Path("TC2"), "log.txt", "log file for TC2")

            archive_builder.export_archive(Path("/workspaces/results-builder/export-test.zip"))

    """

    results_file_name = "results.json"

    def __init__(self):
        """
        Create a new ArchiveBuilder
        """
        self.result_model: Optional[TestResultsSummary] = None

        # TODO - Refactor to interior class instead of opaque tuple
        self.included_artifacts: List[(Path, Path)] = []

    def set_results(self, test_results_summary: TestResultsSummary):
        """Assigns a TestResultsSummary object to this ArchiveBuilder. Required to export the archive."""
        self.result_model = test_results_summary

    def include_artifact(self, artifact_local_path: Path, within_archive_path: Path, name: str, descrption: str = "") -> Artifact:
        """
        Includes an artifact in the ArchiveBuilder and returns a newly created Artifact datamodel instance to be used within other datamodels.

        Args:
            artifact_local_path (Path) - Pathlib path where artifact is currently stored on the machine
            name (str) - Name to artifact for record keeping (NOT FILE NAME)
            description (str) - Description of artifact to include in the exported archive
            within_archive_path - Path to directory to store artifact within an archive. For example: Path("TestGroup1/TestCase1/file1.txt")

        Returns:

            Artifact
                Newly created Artifact datamodel instance to be added to other datamodels that can hold Artifacts (e.g. TestCase)
                Ensures exported archive paths match the paths defined in results.json

        """
        self.included_artifacts.append(
            (artifact_local_path, within_archive_path))

        return Artifact(
            name=name,
            description=descrption,
            path=str(within_archive_path)
        )

    def export_archive(self, output_file: Path = Path("./results.zip")):
        """
        Creates an archive at the specified path containing
             - results.json
             - included artifacts
        """

        if self.result_model is None:
            raise Exception("Unable to export archive because results are None. Use 'set_results()` first!")

        zip_obj = ZipFile(output_file, "w")

        for local_path, archive_path in self.included_artifacts:
            zip_obj.write(str(local_path), str(archive_path))

        zip_obj.writestr("results.json", self.result_model.model_dump_json(
            exclude_none=True, by_alias=True))


class TestResultsBase(ABC):

    @property
    def schemaVersion(self) -> Literal[1]:
        return 1

    @property
    @abstractmethod
    def testMetadata(self) -> TestMetadata:
        pass

    @property
    @abstractmethod
    def testbedComponents(self) -> List[TestbedComponent]:
        pass

    @property
    @abstractmethod
    def testLab(self) -> TestLab:
        pass

    @property
    @abstractmethod
    def testSpecifications(self) -> List[TestSpecification]:
        pass

    @property
    @abstractmethod
    def testResults(self) -> List[TestSpecification]:
        pass

    @property
    @abstractmethod
    def notes(self) -> Optional[List[TestNote]]:
        pass

    @property
    def testResultsSummary(self) -> TestResultsSummary:
        return TestResultsSummary(
            schemaVersion=self.schemaVersion,
            testMetadata=self.testMetadata,
            testbedComponents=self.testbedComponents,
            testLab=self.testLab,
            testSpecifications=self.testSpecifications,
            testResults=self.testResults,
            notes=self.notes
        )
