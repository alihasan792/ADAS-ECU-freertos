"""
JUnit XML Report Generator for ADAS ECU Automated Test Harness.
Produces standard Jenkins/GitHub Actions compatible JUnit XML test results.
"""

from pathlib import Path
from xml.dom import minidom
import xml.etree.ElementTree as ET

from harness.models import RunSummary, TestStatus


class JUnitReporter:
    """Exports test run results to standard JUnit XML format."""

    @staticmethod
    def generate_report(summary: RunSummary, output_dir: str = "reports") -> str:
        run_dir = Path(output_dir) / "runs" / summary.run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        xml_path = run_dir / "junit.xml"

        root = ET.Element("testsuites", {
            "name": "ADAS_ECU_Validation_Suite",
            "tests": str(summary.total_tests),
            "failures": str(summary.failed_tests),
            "skipped": str(summary.skipped_tests),
            "time": f"{summary.duration_ms / 1000.0:.3f}"
        })

        for suite_name, suite_res in summary.suites.items():
            ts = ET.SubElement(root, "testsuite", {
                "name": suite_name,
                "tests": str(suite_res.total),
                "failures": str(suite_res.failed),
                "skipped": str(suite_res.skipped),
                "time": f"{suite_res.duration_ms / 1000.0:.3f}"
            })

            for result in suite_res.test_results:
                tc = ET.SubElement(ts, "testcase", {
                    "classname": f"adas_ecu.{suite_name}",
                    "name": f"{result.test_id}_{result.name.replace(' ', '_')}",
                    "time": f"{result.duration_ms / 1000.0:.3f}"
                })

                if result.status == TestStatus.FAILED:
                    failure = ET.SubElement(tc, "failure", {
                        "message": result.failure_reason or "Test Assertion Failed",
                        "type": "AssertionError"
                    })
                    failure.text = f"Failure: {result.failure_reason}\nLogs:\n" + "\n".join(result.logs)
                elif result.status == TestStatus.SKIPPED:
                    ET.SubElement(tc, "skipped", {"message": "Test skipped"})

        # Pretty-print XML
        xml_str = minidom.parseString(ET.tostring(root, "utf-8")).toprettyxml(indent="  ")
        with open(xml_path, "w", encoding="utf-8") as f:
            f.write(xml_str)

        return str(xml_path)
