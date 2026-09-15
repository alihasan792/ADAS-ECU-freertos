"""
Interactive Terminal Menu for ADAS ECU Automated Test Harness.
Implements the 10-option interactive menu defined in PRD Section 7.
"""

from pathlib import Path
import json
import sys
from typing import Optional

from harness.runner import TestRunner


def run_interactive_menu(runner: TestRunner) -> int:
    """Displays interactive text menu and dispatches user actions."""
    runner.discover_tests()

    while True:
        print("\n==================================================")
        print("      ADAS ECU AUTOMATED TEST HARNESS             ")
        print("==================================================")
        print("1. Run All Tests")
        print("2. Run Smoke Tests")
        print("3. Run Safety Tests")
        print("4. Run CAN Tests")
        print("5. Run Sensor/Functional Tests")
        print("6. Run Fault Injection Tests")
        print("7. Run Single Test")
        print("8. View Last Result")
        print("9. Generate Report")
        print("10. Exit")
        print("==================================================")

        try:
            choice = input("Select an option (1-10): ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            return 0

        if choice == "1":
            res = runner.run()
            if res.failed_tests > 0:
                print(f"\n[INFO] Run finished with {res.failed_tests} failure(s).")
        elif choice == "2":
            runner.run(suite_filter="smoke")
        elif choice == "3":
            runner.run(suite_filter="safety")
        elif choice == "4":
            runner.run(suite_filter="can")
        elif choice == "5":
            runner.run(suite_filter="functional")
        elif choice == "6":
            runner.run(suite_filter="fault")
        elif choice == "7":
            test_id = input("Enter Test ID (e.g. TC-SAF-001): ").strip()
            if test_id:
                runner.run(test_id_filter=test_id)
        elif choice == "8":
            latest_path = Path(runner.output_dir) / "latest_run.json"
            if latest_path.exists():
                with open(latest_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                sum_path = Path(data.get("summary_path", ""))
                if sum_path.exists():
                    with open(sum_path, "r", encoding="utf-8") as f:
                        s_data = json.load(f)
                    print(f"\n--- Last Run ({s_data['run_id']}) ---")
                    print(f"Total: {s_data['total_tests']} | Passed: {s_data['passed_tests']} | Failed: {s_data['failed_tests']} | Pass Rate: {s_data['pass_rate']}%")
                    if s_data['failed_test_ids']:
                        print("Failed IDs: " + ", ".join(s_data['failed_test_ids']))
                else:
                    print("Summary file not found.")
            else:
                print("No previous test runs recorded.")
        elif choice == "9":
            latest_path = Path(runner.output_dir) / "latest_run.json"
            if latest_path.exists():
                print(f"Reports are available in: {runner.output_dir}/")
                print(f"  • HTML Dashboard: {runner.output_dir}/latest_report.html")
                print(f"  • Summary JSON:   {runner.output_dir}/runs/.../summary.json")
                print(f"  • JUnit XML:      {runner.output_dir}/runs/.../junit.xml")
            else:
                print("No runs available to generate reports for. Run tests first.")
        elif choice == "10":
            print("Exiting ADAS ECU Test Harness. Goodbye!")
            return 0
        else:
            print("Invalid selection. Please enter a number between 1 and 10.")
