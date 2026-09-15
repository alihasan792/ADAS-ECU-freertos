"""
JSON Report and Failure Evidence Generator.
Stores machine-readable test execution summaries and bundles failure evidence directories:
reports/runs/<run_id>/
├── summary.json
└── evidence/
    └── <test_id>/
        ├── result.json
        ├── execution.log
        ├── input.json
        └── output.json
"""

from pathlib import Path
from typing import Optional
import json
import os

from harness.models import RunSummary, TestResult, TestStatus


class JSONReporter:
    """Exports test runs to structured JSON and captures artifact evidence."""

    @staticmethod
    def generate_report(summary: RunSummary, output_dir: str = "reports") -> str:
        """Writes the run summary JSON and per-failure evidence files."""
        run_dir = Path(output_dir) / "runs" / summary.run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        # 1. Capture evidence for each test (or failed test)
        evidence_base = run_dir / "evidence"
        for suite_name, suite_res in summary.suites.items():
            for result in suite_res.test_results:
                # Create evidence folder for failed/error tests (or all if desired)
                if result.status in (TestStatus.FAILED, TestStatus.ERROR):
                    test_ev_dir = evidence_base / result.test_id
                    test_ev_dir.mkdir(parents=True, exist_ok=True)
                    result.evidence_dir = str(test_ev_dir)

                    # result.json
                    with open(test_ev_dir / "result.json", "w", encoding="utf-8") as f:
                        json.dump(result.to_dict(), f, indent=2)

                    # input.json
                    with open(test_ev_dir / "input.json", "w", encoding="utf-8") as f:
                        json.dump(result.input_data, f, indent=2)

                    # output.json
                    with open(test_ev_dir / "output.json", "w", encoding="utf-8") as f:
                        json.dump(result.actual, f, indent=2)

                    # execution.log
                    with open(test_ev_dir / "execution.log", "w", encoding="utf-8") as f:
                        f.write(f"=== Execution Log for {result.test_id} ({result.name}) ===\n")
                        f.write(f"Status: {result.status.value}\n")
                        f.write(f"Duration: {result.duration_ms:.2f} ms\n")
                        if result.failure_reason:
                            f.write(f"Failure Reason: {result.failure_reason}\n\n")
                        f.write("Logs:\n")
                        for line in result.logs:
                            f.write(f"  {line}\n")

        # 2. Write master summary.json
        summary_path = run_dir / "summary.json"
        summary.report_path = str(summary_path)
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary.to_dict(), f, indent=2)

        # 3. Create or update latest pointer
        latest_file = Path(output_dir) / "latest_run.json"
        with open(latest_file, "w", encoding="utf-8") as f:
            json.dump({"latest_run_id": summary.run_id, "summary_path": str(summary_path)}, f, indent=2)

        return str(summary_path)
