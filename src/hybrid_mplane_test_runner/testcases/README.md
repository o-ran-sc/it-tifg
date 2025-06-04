# Test Discovery and Execution Framework

This directory contains the test cases and test framework for the Hybrid M-Plane Test Runner.

## Test Case Structure

Test cases in this framework follow a specific structure:

1. Each test case is defined in a separate Python module with a filename pattern of `tc_hmp_XXX.py`, where `XXX` is the test case number.
2. Each test case module contains a class that inherits from `HybridMPlaneTestCase`.
3. Test case classes must implement the `run()` method, which executes the test logic and returns a `TestCase` model.

## Test Discovery

The framework includes a dynamic test discovery mechanism that automatically finds and loads test cases based on:

- Module naming patterns (`tc_hmp_*.py`)
- Class inheritance (subclasses of `HybridMPlaneTestCase`)

Test cases can be organized into:

- **Categories**: Logical groupings of related test cases (e.g., "connectivity", "performance")
- **Test Suites**: Collections of test cases that should be executed together

## Test Groups

The framework uses the `TestGroup` concept to organize test cases in the results. When running a test suite, category, or selected test cases, the results are organized into a `TestGroup` structure:

- **Test Suite**: All test cases in a suite are grouped into a `TestGroup` with the suite name
- **Category**: All test cases in a category are grouped into a `TestGroup` with the category name
- **Selected Test Cases**: Explicitly selected test cases are grouped into a `TestGroup` named "Selected Test Cases"

This hierarchical organization makes it easier to understand the relationship between test cases and provides a more structured view of test results.

## Defining Test Cases

To create a new test case:

1. Create a new Python module with a filename following the pattern `tc_hmp_XXX.py`.
2. Define a class that inherits from `HybridMPlaneTestCase`.
3. Implement the required methods and attributes.

Example:

```python
from hybrid_mplane_test_runner.testcases.base import HybridMPlaneTestCase
import hybrid_mplane_test_runner.models.testresult_models as models

class TestCase_002(HybridMPlaneTestCase):
    # Define categories and suite for test discovery
    categories = ["basic", "configuration"]
    suite = "Basic Configuration"

    def __init__(self, controller=None):
        super().__init__("002", 
                         "Configuration Test", 
                         "Tests basic configuration capabilities",
                         controller=controller)

    def run(self) -> models.TestCase:
        # Test implementation
        # ...
        return self.get_test_case_model()
```

## Test Execution Pipeline

The test execution pipeline provides hooks for setup and teardown operations at different levels:

- **Global**: Executed once before/after all test suites
- **Suite**: Executed before/after each test suite
- **Test Case**: Executed before/after each test case

## Configuration

Test execution can be configured in the `default.json` configuration file:

```json
"test_execution": {
  "comment": "Uncomment one of the following options to control which tests are executed",
  "_test_cases": ["001", "002"],
  "_categories": ["basic", "connectivity"],
  "_suites": ["Basic Connectivity"]
}
```

To enable a specific execution mode, remove the underscore prefix from the desired option.

## Adding Setup and Teardown Hooks

You can add setup and teardown hooks at different levels:

```python
# Global hooks
pipeline.add_global_setup_hook(my_setup_function)
pipeline.add_global_teardown_hook(my_teardown_function)

# Suite hooks
suite = discovery.get_test_suite("My Suite")
suite.add_setup_hook(my_suite_setup)
suite.add_teardown_hook(my_suite_teardown)
```

## Creating Custom Test Suites

You can create custom test suites programmatically:

```python
from hybrid_mplane_test_runner.testcases.discovery import TestSuite

# Create a new test suite
my_suite = TestSuite("My Custom Suite", "Description of the suite")

# Add test cases to the suite
my_suite.add_test_case(TestCase_001)
my_suite.add_test_case(TestCase_002)

# Add the suite to the discovery
discovery._test_suites["My Custom Suite"] = my_suite
```
