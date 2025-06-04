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

"""
Test case discovery module for the Hybrid M-Plane Test Runner.

This module provides functionality to dynamically discover test cases,
organize them into test suites and categories, and create a test execution
pipeline with hooks for setup and teardown.
"""

import importlib
import inspect
import logging
import os
import pkgutil
import sys
from typing import Dict, List, Optional, Set, Type, Tuple, Callable

from hybrid_mplane_test_runner.testcases.base import HybridMPlaneTestCase
import hybrid_mplane_test_runner.models.testresult_models as models


class TestSuite:
    """
    Represents a collection of test cases grouped together.

    A test suite is a logical grouping of test cases that can be executed
    together. It provides hooks for setup and teardown operations that
    should be performed before and after the execution of the test cases.

    :ivar name: The name of the test suite.
    :type name: str
    :ivar description: A description of the test suite.
    :type description: str
    :ivar test_cases: A list of test case classes in this suite.
    :type test_cases: List[Type[HybridMPlaneTestCase]]
    :ivar categories: A set of categories this test suite belongs to.
    :type categories: Set[str]
    """

    def __init__(self, name: str, description: str = ""):
        """
        Initialize a new test suite.

        :param name: The name of the test suite.
        :type name: str
        :param description: A description of the test suite.
        :type description: str
        """
        self.name = name
        self.description = description
        self.test_cases: List[Type[HybridMPlaneTestCase]] = []
        self.categories: Set[str] = set()
        self._setup_hooks: List[Callable] = []
        self._teardown_hooks: List[Callable] = []

    def add_test_case(self, test_case_class: Type[HybridMPlaneTestCase]) -> None:
        """
        Add a test case to this suite.

        :param test_case_class: The test case class to add.
        :type test_case_class: Type[HybridMPlaneTestCase]
        """
        if test_case_class not in self.test_cases:
            self.test_cases.append(test_case_class)

    def add_category(self, category: str) -> None:
        """
        Add a category to this test suite.

        :param category: The category to add.
        :type category: str
        """
        self.categories.add(category)

    def add_setup_hook(self, hook: Callable) -> None:
        """
        Add a setup hook to be executed before running the test cases.

        :param hook: The setup hook function.
        :type hook: Callable
        """
        self._setup_hooks.append(hook)

    def add_teardown_hook(self, hook: Callable) -> None:
        """
        Add a teardown hook to be executed after running the test cases.

        :param hook: The teardown hook function.
        :type hook: Callable
        """
        self._teardown_hooks.append(hook)

    def run_setup_hooks(self) -> None:
        """
        Run all setup hooks in the order they were added.
        """
        for hook in self._setup_hooks:
            hook()

    def run_teardown_hooks(self) -> None:
        """
        Run all teardown hooks in the order they were added.
        """
        for hook in self._teardown_hooks:
            hook()


class TestDiscovery:
    """
    Provides functionality to discover test cases and organize them into suites.

    This class scans the specified package for test case classes that inherit
    from HybridMPlaneTestCase, and organizes them into test suites based on
    naming conventions or explicit annotations.

    :ivar _test_cases: A dictionary mapping test case IDs to test case classes.
    :type _test_cases: Dict[str, Type[HybridMPlaneTestCase]]
    :ivar _test_suites: A dictionary mapping suite names to TestSuite objects.
    :type _test_suites: Dict[str, TestSuite]
    :ivar _categories: A dictionary mapping category names to sets of test case IDs.
    :type _categories: Dict[str, Set[str]]
    """

    def __init__(self):
        """
        Initialize a new TestDiscovery instance.
        """
        self._test_cases: Dict[str, Type[HybridMPlaneTestCase]] = {}
        self._test_suites: Dict[str, TestSuite] = {}
        self._categories: Dict[str, Set[str]] = {}

    def discover_test_cases(self, package_name: str = "hybrid_mplane_test_runner.testcases") -> None:
        """
        Discover test cases in the specified package.

        This method scans the specified package for modules matching the pattern
        'tc_hmp_*.py', imports them, and finds classes that inherit from
        HybridMPlaneTestCase.

        :param package_name: The name of the package to scan for test cases.
        :type package_name: str
        """
        logging.info(f"Discovering test cases in package: {package_name}")

        # Import the package
        package = importlib.import_module(package_name)
        package_path = os.path.dirname(package.__file__)

        # Scan for modules in the package
        for _, module_name, is_pkg in pkgutil.iter_modules([package_path]):
            if is_pkg:
                # Recursively scan subpackages
                self.discover_test_cases(f"{package_name}.{module_name}")
            elif module_name.startswith("tc_hmp_"):
                # Import the module
                module_path = f"{package_name}.{module_name}"
                try:
                    module = importlib.import_module(module_path)

                    # Find test case classes in the module
                    for name, obj in inspect.getmembers(module):
                        if (inspect.isclass(obj) and 
                            issubclass(obj, HybridMPlaneTestCase) and 
                            obj != HybridMPlaneTestCase):

                            # Extract test case ID from class name or module name
                            tc_id = getattr(obj, "number", None)
                            if not tc_id:
                                # Try to extract from module name (tc_hmp_001 -> 001)
                                tc_id = module_name.split("_")[-1]

                            # Add to test cases dictionary
                            self._test_cases[tc_id] = obj
                            logging.debug(f"Discovered test case: {tc_id} ({obj.__name__})")

                            # Extract categories from class attributes or annotations
                            categories = getattr(obj, "categories", [])
                            for category in categories:
                                if category not in self._categories:
                                    self._categories[category] = set()
                                self._categories[category].add(tc_id)

                            # Extract suite information from class attributes or annotations
                            suite_name = getattr(obj, "suite", "Default")
                            if suite_name not in self._test_suites:
                                self._test_suites[suite_name] = TestSuite(suite_name)
                            self._test_suites[suite_name].add_test_case(obj)

                except ImportError as e:
                    logging.error(f"Error importing module {module_path}: {e}")
                except Exception as e:
                    logging.error(f"Error processing module {module_path}: {e}")

        logging.info(f"Discovered {len(self._test_cases)} test cases in {len(self._test_suites)} suites")

    def get_test_case(self, tc_id: str) -> Optional[Type[HybridMPlaneTestCase]]:
        """
        Get a test case class by its ID.

        :param tc_id: The ID of the test case.
        :type tc_id: str
        :return: The test case class, or None if not found.
        :rtype: Optional[Type[HybridMPlaneTestCase]]
        """
        return self._test_cases.get(tc_id)

    def get_all_test_cases(self) -> List[Type[HybridMPlaneTestCase]]:
        """
        Get all discovered test case classes.

        :return: A list of all test case classes.
        :rtype: List[Type[HybridMPlaneTestCase]]
        """
        return list(self._test_cases.values())

    def get_test_suite(self, name: str) -> Optional[TestSuite]:
        """
        Get a test suite by its name.

        :param name: The name of the test suite.
        :type name: str
        :return: The test suite, or None if not found.
        :rtype: Optional[TestSuite]
        """
        return self._test_suites.get(name)

    def get_all_test_suites(self) -> List[TestSuite]:
        """
        Get all discovered test suites.

        :return: A list of all test suites.
        :rtype: List[TestSuite]
        """
        return list(self._test_suites.values())

    def get_test_cases_by_category(self, category: str) -> List[Type[HybridMPlaneTestCase]]:
        """
        Get all test cases in a specific category.

        :param category: The category name.
        :type category: str
        :return: A list of test case classes in the specified category.
        :rtype: List[Type[HybridMPlaneTestCase]]
        """
        if category not in self._categories:
            return []

        return [self._test_cases[tc_id] for tc_id in self._categories[category] if tc_id in self._test_cases]

    def get_all_categories(self) -> List[str]:
        """
        Get all discovered categories.

        :return: A list of all category names.
        :rtype: List[str]
        """
        return list(self._categories.keys())


class TestExecutionPipeline:
    """
    Manages the execution of test cases with setup and teardown hooks.

    This class provides a pipeline for executing test cases with hooks for
    setup and teardown operations at various stages of the execution.

    :ivar _discovery: The test discovery instance used to find test cases.
    :type _discovery: TestDiscovery
    :ivar _global_setup_hooks: A list of global setup hooks.
    :type _global_setup_hooks: List[Callable]
    :ivar _global_teardown_hooks: A list of global teardown hooks.
    :type _global_teardown_hooks: List[Callable]
    """

    def __init__(self, discovery: TestDiscovery):
        """
        Initialize a new TestExecutionPipeline instance.

        :param discovery: The test discovery instance to use.
        :type discovery: TestDiscovery
        """
        self._discovery = discovery
        self._global_setup_hooks: List[Callable] = []
        self._global_teardown_hooks: List[Callable] = []

    def add_global_setup_hook(self, hook: Callable) -> None:
        """
        Add a global setup hook to be executed before any test suite.

        :param hook: The setup hook function.
        :type hook: Callable
        """
        self._global_setup_hooks.append(hook)

    def add_global_teardown_hook(self, hook: Callable) -> None:
        """
        Add a global teardown hook to be executed after all test suites.

        :param hook: The teardown hook function.
        :type hook: Callable
        """
        self._global_teardown_hooks.append(hook)

    def run_test_case(self, test_case_class: Type[HybridMPlaneTestCase], controller) -> models.TestCase:
        """
        Run a single test case.

        :param test_case_class: The test case class to run.
        :type test_case_class: Type[HybridMPlaneTestCase]
        :param controller: The controller to use for the test case.
        :return: The test case result.
        :rtype: models.TestCase
        """
        test_case = test_case_class(controller)
        return test_case.run()

    def run_test_suite(self, suite: TestSuite, controller) -> models.TestGroup:
        """
        Run all test cases in a test suite and return them as a TestGroup.

        :param suite: The test suite to run.
        :type suite: TestSuite
        :param controller: The controller to use for the test cases.
        :return: A TestGroup containing all test case results.
        :rtype: models.TestGroup
        """
        results = []

        try:
            # Run suite setup hooks
            suite.run_setup_hooks()

            # Run each test case in the suite
            for test_case_class in suite.test_cases:
                result = self.run_test_case(test_case_class, controller)
                results.append(result)
        finally:
            # Run suite teardown hooks (even if an exception occurs)
            suite.run_teardown_hooks()

        # Create a TestGroup for the suite
        # Determine the group number based on the first test case
        group_number = "0"  # Default to "0" if no valid test cases exist
        if suite.test_cases:
            # Create a temporary instance to get the number attribute
            try:
                temp_instance = suite.test_cases[0](None)  # Pass None as controller
                group_number = f"{temp_instance.number.split('.')[0]}"
            except Exception as e:
                logging.warning(
                    f"Failed to create temporary instance of {suite.test_cases[0].__name__} to get number attribute: {e}. "
                    "Using default group number as '0'."
                )

        test_group = models.TestGroup(
            number=group_number,
            name=suite.name,
            description=suite.description,
            groupItems=results
        )

        return test_group

    def run_all_test_suites(self, controller) -> List[models.TestGroup]:
        """
        Run all discovered test suites.

        :param controller: The controller to use for the test cases.
        :return: A list of TestGroup objects, one for each test suite.
        :rtype: List[models.TestGroup]
        """
        results = []

        try:
            # Run global setup hooks
            for hook in self._global_setup_hooks:
                hook()

            # Run each test suite
            for suite_name, suite in self._discovery._test_suites.items():
                suite_results = self.run_test_suite(suite, controller)
                results.append(suite_results)
        finally:
            # Run global teardown hooks (even if an exception occurs)
            for hook in self._global_teardown_hooks:
                hook()

        return results

    def run_test_cases_by_category(self, category: str, controller) -> models.TestGroup:
        """
        Run all test cases in a specific category and return them as a TestGroup.

        :param category: The category name.
        :type category: str
        :param controller: The controller to use for the test cases.
        :return: A TestGroup containing all test case results for the category.
        :rtype: models.TestGroup
        """
        results = []
        test_cases = self._discovery.get_test_cases_by_category(category)

        for test_case_class in test_cases:
            result = self.run_test_case(test_case_class, controller)
            results.append(result)

        # Create a TestGroup for the category
        # Determine the group number based on the first test case
        group_number = "0"  # Default to "0" if no valid test cases exist
        if test_cases:
            # Create a temporary instance to get the number attribute
            try:
                temp_instance = test_cases[0](None)  # Pass None as controller
                group_number = f"{temp_instance.number.split('.')[0]}"
            except Exception as e:
                logging.warning(
                    f"Failed to create temporary instance of {test_cases[0].__name__} to get number attribute: {e}. "
                    "Using default group number as '0'."
                )

        test_group = models.TestGroup(
            number=group_number,
            name=f"Category: {category}",
            description=f"Test cases in category '{category}'",
            groupItems=results
        )

        return test_group

    def run_selected_test_cases(self, test_case_ids: List[str], controller) -> models.TestGroup:
        """
        Run selected test cases by their IDs and return them as a TestGroup.

        :param test_case_ids: A list of test case IDs to run.
        :type test_case_ids: List[str]
        :param controller: The controller to use for the test cases.
        :return: A TestGroup containing all test case results.
        :rtype: models.TestGroup
        """
        results = []
        test_case_classes = []

        for tc_id in test_case_ids:
            test_case_class = self._discovery.get_test_case(tc_id)
            if test_case_class:
                test_case_classes.append(test_case_class)
                result = self.run_test_case(test_case_class, controller)
                results.append(result)
            else:
                logging.warning(f"Test case with ID {tc_id} not found")

        # Create a TestGroup for the selected test cases
        # Determine the group number based on the first test case
        group_number = "0"  # Default to "0" if no valid test cases exist
        if test_case_classes:
            # Create a temporary instance to get the number attribute
            try:
                temp_instance = test_case_classes[0](None)  # Pass None as controller
                group_number = f"{temp_instance.number.split('.')[0]}"
            except Exception as e:
                logging.warning(
                    f"Failed to create temporary instance of {test_case_classes[0].__name__} to get number attribute: {e}. "
                    "Using default group number as '0'."
                )

        test_group = models.TestGroup(
            number=group_number,
            name="Selected Test Cases",
            description=f"Test cases with IDs: {', '.join(test_case_ids)}",
            groupItems=results
        )

        return test_group


# Helper function to create a test execution pipeline
def create_test_pipeline() -> Tuple[TestDiscovery, TestExecutionPipeline]:
    """
    Create and initialize a test discovery and execution pipeline.

    This function discovers all test cases and creates a test execution
    pipeline ready to run tests.

    :return: A tuple containing the test discovery and execution pipeline.
    :rtype: Tuple[TestDiscovery, TestExecutionPipeline]
    """
    discovery = TestDiscovery()
    discovery.discover_test_cases()
    pipeline = TestExecutionPipeline(discovery)
    return discovery, pipeline
