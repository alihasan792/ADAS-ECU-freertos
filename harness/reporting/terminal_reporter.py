"""
Terminal Report Generator for ADAS ECU Automated Test Harness.
Renders clean ANSI-colored execution tables and summary blocks matching PRD Section 19.
"""

import sys
from typing import List, Optional
from harness.models import RunSummary, TestResult, TestStatus


class TerminalColors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    RESET = "\033[0m"


class TerminalReporter:
    """Formats and prints test results to standard output."""

    def __init__(self, use_color: bool = True):
        # Disable colors if stdout is redirected or on unsupported terminals
        self.use_color = use_color and sys.stdout.isatty()

    def _c(self, text: str, color: str) -> str:
        if self.use_color:
            return f"{color}{text}{TerminalColors.RESET}"
        return text

    def print_header(self, title: str) -> None:
        bar = "=" * 60
        print(self._c(f"\n{bar}", TerminalColors.CYAN))
        print(self._c(f"  {title.upper()}", TerminalColors.BOLD + TerminalColors.CYAN))
        print(self._c(f"{bar}\n", TerminalColors.CYAN))

    def print_test_start(self, test_index: int, total: int, test_id: str, name: str) -> None:
        idx_str = f"[{test_index}/{total}]"
        print(f"{self._c(idx_str, TerminalColors.BLUE)} {self._c(test_id, TerminalColors.BOLD)}: {name} ... ", end="", flush=True)

    def print_test_result(self, result: TestResult) -> None:
        dur_str = f"({result.duration_ms:.1f}ms)"
        if result.status == TestStatus.PASSED:
            status_str = self._c("PASS", TerminalColors.GREEN)
        elif result.status == TestStatus.FAILED:
            status_str = self._c("FAIL", TerminalColors.RED)
        elif result.status == TestStatus.SKIPPED:
            status_str = self._c("SKIP", TerminalColors.YELLOW)
        else:
            status_str = self._c("ERROR", TerminalColors.RED)
        print(f"[{status_str}] {dur_str}")
        if result.status in (TestStatus.FAILED, TestStatus.ERROR) and result.failure_reason:
            print(self._c(f"    Reason: {result.failure_reason}", TerminalColors.YELLOW))

    def print_summary(self, summary: RunSummary) -> None:
        bar = "=" * 60
        print(self._c(f"\n{bar}", TerminalColors.CYAN))
        print(self._c("               TEST EXECUTION SUMMARY", TerminalColors.BOLD))
        print(self._c(f"{bar}", TerminalColors.CYAN))

        print(f"Total Tests : {self._c(str(summary.total_tests), TerminalColors.BOLD)}")
        print(f"Passed      : {self._c(str(summary.passed_tests), TerminalColors.GREEN)}")
        print(f"Failed      : {self._c(str(summary.failed_tests), TerminalColors.RED if summary.failed_tests > 0 else TerminalColors.GREEN)}")
        print(f"Skipped     : {self._c(str(summary.skipped_tests), TerminalColors.YELLOW)}")

        rate_color = TerminalColors.GREEN if summary.pass_rate >= 100.0 else (TerminalColors.YELLOW if summary.pass_rate >= 80.0 else TerminalColors.RED)
        print(f"Pass Rate   : {self._c(f'{summary.pass_rate:.1f}%', rate_color + TerminalColors.BOLD)}")
        print(f"Duration    : {summary.duration_ms:.1f} ms")

        # Suite breakdown
        if summary.suites:
            print("\nSuite Breakdown:")
            for suite_name, suite_res in summary.suites.items():
                print(f"  * {suite_name.capitalize():<12}: {suite_res.passed}/{suite_res.total} passed ({suite_res.pass_rate:.0f}%) in {suite_res.duration_ms:.1f}ms")

        # Failures list
        if summary.failed_test_ids:
            print(self._c("\nFailed Tests:", TerminalColors.RED + TerminalColors.BOLD))
            for failed_id in summary.failed_test_ids:
                # Find test result
                name = ""
                for s in summary.suites.values():
                    for t in s.test_results:
                        if t.test_id == failed_id:
                            name = t.name
                            break
                print(self._c(f"  [X] {failed_id:<12} {name}", TerminalColors.RED))

        if summary.report_path:
            print(f"\nReport Generated:\n  {summary.report_path}")

        print(self._c(f"{bar}\n", TerminalColors.CYAN))
