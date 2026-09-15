"""
Data models for the ADAS ECU Automated Test Harness.
Defines schemas for test cases, results, execution summaries, and system states.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional
import datetime


class TestStatus(str, Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    ERROR = "ERROR"


class Priority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SystemState(str, Enum):
    INIT = "INIT"
    RUNNING = "RUNNING"
    SAFE = "SAFE"
    FAULT = "FAULT"


class CollisionRisk(str, Enum):
    NONE = "NONE"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass
class TestCase:
    """Represents the static definition and metadata of a test case."""
    id: str
    name: str
    suite: str
    description: str
    priority: Priority = Priority.MEDIUM
    tags: List[str] = field(default_factory=list)
    requirement_id: Optional[str] = None
    preconditions: Optional[str] = None
    input_data: Dict[str, Any] = field(default_factory=dict)
    expected: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["priority"] = self.priority.value
        return d


@dataclass
class TestResult:
    """Represents the execution outcome and captured evidence of a test case."""
    test_id: str
    name: str
    suite: str
    status: TestStatus
    duration_ms: float
    input_data: Dict[str, Any] = field(default_factory=dict)
    expected: Dict[str, Any] = field(default_factory=dict)
    actual: Dict[str, Any] = field(default_factory=dict)
    failure_reason: Optional[str] = None
    evidence_dir: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z")
    logs: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d


@dataclass
class SuiteResult:
    """Summary of execution for an entire test suite."""
    suite_name: str
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    duration_ms: float = 0.0
    test_results: List[TestResult] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return round((self.passed / self.total) * 100.0, 2)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "suite_name": self.suite_name,
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "pass_rate": self.pass_rate,
            "duration_ms": round(self.duration_ms, 2),
            "test_results": [r.to_dict() for r in self.test_results]
        }


@dataclass
class RunSummary:
    """Overall test run execution summary across all requested suites."""
    run_id: str
    timestamp: str = field(default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z")
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    duration_ms: float = 0.0
    suites: Dict[str, SuiteResult] = field(default_factory=dict)
    failed_test_ids: List[str] = field(default_factory=list)
    report_path: Optional[str] = None

    @property
    def pass_rate(self) -> float:
        if self.total_tests == 0:
            return 0.0
        return round((self.passed_tests / self.total_tests) * 100.0, 2)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "skipped_tests": self.skipped_tests,
            "pass_rate": self.pass_rate,
            "duration_ms": round(self.duration_ms, 2),
            "failed_test_ids": self.failed_test_ids,
            "suites": {k: v.to_dict() for k, v in self.suites.items()},
            "report_path": self.report_path
        }
