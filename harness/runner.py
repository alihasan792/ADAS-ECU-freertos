"""
Test Runner Engine for ADAS ECU Automated Test Harness.
Executes test cases following the strict 8-stage lifecycle:
Setup -> Input -> Execute -> Capture -> Validate -> Collect Evidence -> Cleanup -> Store.
"""

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type
import datetime
import importlib
import json
import time
import traceback

from harness.assertions import HarnessAssertionError
from harness.models import (
    Priority, RunSummary, SuiteResult, TestCase, TestResult, TestStatus
)
from harness.reporting.html_reporter import HTMLReporter
from harness.reporting.json_reporter import JSONReporter
from harness.reporting.junit_reporter import JUnitReporter
from harness.reporting.terminal_reporter import TerminalReporter


class TestRunner:
    """Orchestrates test suites, runs test lifecycle, and outputs reports."""

    def __init__(self, config_path: str = "config/default_config.json", output_dir: str = "reports"):
        self.output_dir = output_dir
        self.config = self._load_config(config_path)
        self.terminal_reporter = TerminalReporter()
        self.registry: Dict[str, List[TestCase]] = {}
        self.test_callables: Dict[str, Callable[[TestCase, TestResult], None]] = {}

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        p = Path(config_path)
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"test_timeout_ms": 5000, "reports_directory": "reports"}

    def register_test(self, test_case: TestCase, test_func: Callable[[TestCase, TestResult], None]) -> None:
        suite = test_case.suite.lower()
        if suite not in self.registry:
            self.registry[suite] = []
        self.registry[suite].append(test_case)
        self.test_callables[test_case.id] = test_func

    def discover_tests(self) -> None:
        """Dynamically imports all suites from tests/suites."""
        suite_modules = [
            "tests.suites.smoke_suite",
            "tests.suites.functional_suite",
            "tests.suites.safety_suite",
            "tests.suites.can_suite",
            "tests.suites.fault_suite"
        ]
        for mod_name in suite_modules:
            try:
                mod = importlib.import_module(mod_name)
                if hasattr(mod, "register_tests"):
                    mod.register_tests(self)
            except Exception as e:
                print(f"Warning: Failed to import {mod_name}: {e}")

    def execute_test(self, test_case: TestCase) -> TestResult:
        """Executes the complete test lifecycle for a single test case."""
        result = TestResult(
            test_id=test_case.id,
            name=test_case.name,
            suite=test_case.suite,
            status=TestStatus.PASSED,
            duration_ms=0.0,
            input_data=copy_dict(test_case.input_data),
            expected=copy_dict(test_case.expected),
            actual={}
        )

        test_func = self.test_callables.get(test_case.id)
        if not test_func:
            result.status = TestStatus.ERROR
            result.failure_reason = f"No implementation found for {test_case.id}"
            return result

        start_time = time.perf_counter()
        try:
            # Lifecycle: Setup & Execute
            result.logs.append(f"Starting test {test_case.id}: {test_case.name}")
            result.logs.append(f"Description: {test_case.description}")
            if test_case.requirement_id:
                result.logs.append(f"Traceable to: {test_case.requirement_id}")

            test_func(test_case, result)
            result.status = TestStatus.PASSED
            result.logs.append(f"Test {test_case.id} PASSED.")

        except HarnessAssertionError as ae:
            result.status = TestStatus.FAILED
            result.failure_reason = ae.message
            if ae.expected is not None:
                result.expected["assertion_expected"] = ae.expected
            if ae.actual is not None:
                result.actual["assertion_actual"] = ae.actual
            result.logs.append(f"ASSERTION FAILED: {ae.message}")

        except Exception as ex:
            result.status = TestStatus.ERROR
            result.failure_reason = f"Execution Exception: {type(ex).__name__}: {str(ex)}"
            result.logs.append(f"ERROR: {traceback.format_exc()}")

        finally:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            result.duration_ms = round(elapsed_ms, 2)
            result.logs.append(f"Execution completed in {result.duration_ms:.2f} ms")

        return result

    def run(
        self,
        suite_filter: Optional[str] = None,
        test_id_filter: Optional[str] = None,
        priority_filter: Optional[Priority] = None,
        tag_filter: Optional[str] = None,
        failed_only: bool = False
    ) -> RunSummary:
        """Filters test cases and runs them, producing reports."""
        self.discover_tests()

        # Collect tests
        selected_tests: List[TestCase] = []
        for suite_name, tests in self.registry.items():
            for t in tests:
                selected_tests.append(t)

        # Apply failed_only filter
        if failed_only:
            latest_path = Path(self.output_dir) / "latest_run.json"
            if latest_path.exists():
                with open(latest_path, "r", encoding="utf-8") as f:
                    latest_info = json.load(f)
                summary_file = Path(latest_info.get("summary_path", ""))
                if summary_file.exists():
                    with open(summary_file, "r", encoding="utf-8") as f:
                        prev_summary = json.load(f)
                    failed_ids = set(prev_summary.get("failed_test_ids", []))
                    selected_tests = [t for t in selected_tests if t.id in failed_ids]
            else:
                selected_tests = []

        # Apply suite filter
        if suite_filter:
            sf = suite_filter.lower()
            selected_tests = [t for t in selected_tests if t.suite.lower() == sf]

        # Apply test_id filter
        if test_id_filter:
            selected_tests = [t for t in selected_tests if t.id.upper() == test_id_filter.upper()]

        # Apply priority filter
        if priority_filter:
            selected_tests = [t for t in selected_tests if t.priority == priority_filter]

        # Apply tag filter
        if tag_filter:
            tf = tag_filter.lower()
            selected_tests = [t for t in selected_tests if tf in [x.lower() for x in t.tags]]

        run_id = datetime.datetime.utcnow().strftime("run_%Y%m%d_%H%M%S")
        summary = RunSummary(run_id=run_id, total_tests=len(selected_tests))

        self.terminal_reporter.print_header(f"ADAS ECU Automated Test Harness ({run_id})")

        total = len(selected_tests)
        overall_start = time.perf_counter()

        for idx, tc in enumerate(selected_tests, start=1):
            self.terminal_reporter.print_test_start(idx, total, tc.id, tc.name)
            result = self.execute_test(tc)
            self.terminal_reporter.print_test_result(result)

            # Record into suite
            s_name = tc.suite.lower()
            if s_name not in summary.suites:
                summary.suites[s_name] = SuiteResult(suite_name=s_name)

            s_res = summary.suites[s_name]
            s_res.total += 1
            s_res.duration_ms += result.duration_ms
            s_res.test_results.append(result)

            if result.status == TestStatus.PASSED:
                s_res.passed += 1
                summary.passed_tests += 1
            elif result.status == TestStatus.FAILED:
                s_res.failed += 1
                summary.failed_tests += 1
                summary.failed_test_ids.append(result.test_id)
            elif result.status == TestStatus.SKIPPED:
                s_res.skipped += 1
                summary.skipped_tests += 1
            else:
                s_res.failed += 1
                summary.failed_tests += 1
                summary.failed_test_ids.append(result.test_id)

        summary.duration_ms = round((time.perf_counter() - overall_start) * 1000.0, 2)

        # Generate Reports
        JSONReporter.generate_report(summary, output_dir=self.output_dir)
        JUnitReporter.generate_report(summary, output_dir=self.output_dir)
        HTMLReporter.generate_report(summary, output_dir=self.output_dir)

        # Print terminal summary
        self.terminal_reporter.print_summary(summary)

        return summary


def copy_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    try:
        return json.loads(json.dumps(d))
    except Exception:
        return {k: str(v) for k, v in d.items()}
