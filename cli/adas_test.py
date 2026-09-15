"""
Primary CLI Entrypoint for ADAS ECU Automated Test Harness.
Supports scriptable direct execution for CI/CD pipelines and interactive terminal usage.
Exit codes:
  0 = All tests passed
  1 = One or more tests failed
  2 = Invalid command or configuration
  3 = Execution error or unexpected exception
"""

from pathlib import Path
import argparse
import json
import os
import sys

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from harness.models import Priority
from harness.runner import TestRunner
from cli.interactive import run_interactive_menu


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="adas-test",
        description="ADAS ECU Automated Validation & Test Harness CLI"
    )

    subparsers = parser.add_subparsers(dest="subcommand", help="Available subcommands")

    # 'run' subcommand
    run_parser = subparsers.add_parser("run", help="Execute test suites or individual tests")
    run_parser.add_argument("--suite", "-s", type=str, choices=["smoke", "functional", "safety", "can", "fault"],
                            help="Target test suite to execute")
    run_parser.add_argument("--all", "-a", action="store_true", help="Execute all test suites")
    run_parser.add_argument("--test", "-t", type=str, help="Execute specific test by ID (e.g. TC-SAF-001)")
    run_parser.add_argument("--priority", "-p", type=str, choices=["critical", "high", "medium", "low"],
                            help="Filter tests by priority level")
    run_parser.add_argument("--failed", "-f", action="store_true", help="Re-run only tests that failed in the last run")
    run_parser.add_argument("--config", "-c", type=str, default="config/default_config.json", help="Path to config file")
    run_parser.add_argument("--output", "-o", type=str, default="reports", help="Reports output directory")

    # 'regression' subcommand
    reg_parser = subparsers.add_parser("regression", help="Execute full regression test suite")
    reg_parser.add_argument("--config", "-c", type=str, default="config/default_config.json", help="Path to config file")
    reg_parser.add_argument("--output", "-o", type=str, default="reports", help="Reports output directory")

    # 'list' subcommand
    list_parser = subparsers.add_parser("list", help="List available test cases and suites")
    list_parser.add_argument("--suite", "-s", type=str, help="Filter list by suite")

    # 'report' subcommand
    rep_parser = subparsers.add_parser("report", help="Display or locate test reports")
    rep_parser.add_argument("--format", type=str, choices=["json", "html", "junit"], default="html",
                            help="Report format to display/open")
    rep_parser.add_argument("--output", "-o", type=str, default="reports", help="Reports output directory")

    # 'interactive' subcommand
    subparsers.add_parser("interactive", help="Start interactive text menu")

    return parser


def main() -> int:
    parser = build_parser()

    # If no arguments provided and connected to terminal, launch interactive menu
    if len(sys.argv) == 1:
        if sys.stdin.isatty():
            runner = TestRunner()
            return run_interactive_menu(runner)
        else:
            parser.print_help()
            return 2

    try:
        args = parser.parse_args()
    except SystemExit as se:
        return 2 if se.code != 0 else 0

    if not args.subcommand:
        parser.print_help()
        return 2

    try:
        if args.subcommand == "interactive":
            runner = TestRunner()
            return run_interactive_menu(runner)

        elif args.subcommand == "list":
            runner = TestRunner()
            runner.discover_tests()
            print("\n=== Registered ADAS ECU Test Cases ===")
            for suite_name, tests in runner.registry.items():
                if args.suite and suite_name.lower() != args.suite.lower():
                    continue
                print(f"\nSuite: {suite_name.upper()} ({len(tests)} tests)")
                for t in tests:
                    req_str = f" [{t.requirement_id}]" if t.requirement_id else ""
                    print(f"  * {t.id:<12} (Prio: {t.priority.value:<8}) {t.name}{req_str}")
            print("")
            return 0

        elif args.subcommand == "report":
            latest_path = Path(args.output) / "latest_run.json"
            if not latest_path.exists():
                print(f"[ERROR] No test runs found in '{args.output}/'. Run tests first.")
                return 2

            with open(latest_path, "r", encoding="utf-8") as f:
                info = json.load(f)
            run_id = info.get("latest_run_id")
            run_dir = Path(args.output) / "runs" / run_id

            if args.format == "html":
                html_path = run_dir / "report.html"
                print(f"HTML Report: {html_path.resolve()}")
            elif args.format == "junit":
                junit_path = run_dir / "junit.xml"
                print(f"JUnit XML Report: {junit_path.resolve()}")
            else:
                json_path = run_dir / "summary.json"
                print(f"JSON Summary: {json_path.resolve()}")
            return 0

        elif args.subcommand == "regression":
            runner = TestRunner(config_path=args.config, output_dir=args.output)
            summary = runner.run(tag_filter="regression")
            return 0 if summary.failed_tests == 0 else 1

        elif args.subcommand == "run":
            runner = TestRunner(config_path=args.config, output_dir=args.output)

            suite = args.suite
            if args.all:
                suite = None

            prio = Priority(args.priority) if args.priority else None

            summary = runner.run(
                suite_filter=suite,
                test_id_filter=args.test,
                priority_filter=prio,
                failed_only=args.failed
            )

            return 0 if summary.failed_tests == 0 else 1

    except FileNotFoundError as fe:
        print(f"[ERROR] File not found: {fe}")
        return 2
    except Exception as ex:
        print(f"[FATAL] Execution error in test harness: {ex}")
        import traceback
        traceback.print_exc()
        return 3

    return 0


if __name__ == "__main__":
    sys.exit(main())
