"""
Assertion Engine for the ADAS ECU Automated Test Harness.
Provides structured assertion utilities with automated error capture for test evidence.
"""

from typing import Any, Optional
import math


class HarnessAssertionError(AssertionError):
    """Specific assertion failure with structured expected and actual data."""
    def __init__(self, message: str, expected: Any = None, actual: Any = None):
        super().__init__(message)
        self.message = message
        self.expected = expected
        self.actual = actual


class Assertions:
    """Reusable assertion methods recording expected vs actual outcomes."""

    @staticmethod
    def assert_equal(actual: Any, expected: Any, msg: Optional[str] = None) -> None:
        """Assert that actual == expected."""
        if actual != expected:
            detail = msg or f"Expected '{expected}', but got '{actual}'"
            raise HarnessAssertionError(detail, expected=expected, actual=actual)

    @staticmethod
    def assert_not_equal(actual: Any, expected: Any, msg: Optional[str] = None) -> None:
        """Assert that actual != expected."""
        if actual == expected:
            detail = msg or f"Expected value not equal to '{expected}', but was identical"
            raise HarnessAssertionError(detail, expected=f"!= {expected}", actual=actual)

    @staticmethod
    def assert_true(expr: bool, msg: Optional[str] = None) -> None:
        """Assert that condition evaluates to True."""
        if not bool(expr):
            detail = msg or "Expected True, but evaluated to False"
            raise HarnessAssertionError(detail, expected=True, actual=False)

    @staticmethod
    def assert_false(expr: bool, msg: Optional[str] = None) -> None:
        """Assert that condition evaluates to False."""
        if bool(expr):
            detail = msg or "Expected False, but evaluated to True"
            raise HarnessAssertionError(detail, expected=False, actual=True)

    @staticmethod
    def assert_within_range(actual: float, expected: float, tolerance: float, msg: Optional[str] = None) -> None:
        """Assert that actual is within expected ± tolerance."""
        diff = abs(actual - expected)
        if diff > tolerance:
            detail = (msg or f"Expected {expected} ± {tolerance} (range [{expected-tolerance:.4f}, {expected+tolerance:.4f}]), "
                             f"but got {actual} (difference {diff:.4f})")
            raise HarnessAssertionError(detail, expected={"value": expected, "tolerance": tolerance}, actual=actual)

    @staticmethod
    def assert_state(actual_state: Any, expected_state: Any, msg: Optional[str] = None) -> None:
        """Assert that the ECU system state matches the expected state."""
        act_str = actual_state.value if hasattr(actual_state, "value") else str(actual_state)
        exp_str = expected_state.value if hasattr(expected_state, "value") else str(expected_state)
        if act_str != exp_str:
            detail = msg or f"ECU State mismatch: Expected '{exp_str}', but got '{act_str}'"
            raise HarnessAssertionError(detail, expected=exp_str, actual=act_str)

    @staticmethod
    def assert_message_received(received: bool, can_id: Optional[int] = None, msg: Optional[str] = None) -> None:
        """Assert that an expected CAN frame was successfully received."""
        if not received:
            id_str = f" (ID: 0x{can_id:X})" if can_id is not None else ""
            detail = msg or f"Expected CAN message{id_str} was not received (timeout)"
            raise HarnessAssertionError(detail, expected="Frame Received", actual="Timeout / Dropped")

    @staticmethod
    def assert_message_timeout(received: bool, msg: Optional[str] = None) -> None:
        """Assert that a CAN message timed out as expected."""
        if received:
            detail = msg or "Expected CAN message timeout, but frame was received"
            raise HarnessAssertionError(detail, expected="Timeout", actual="Frame Received")

    @staticmethod
    def assert_lt(actual: float, bound: float, msg: Optional[str] = None) -> None:
        """Assert that actual < bound."""
        if not (actual < bound):
            detail = msg or f"Expected value < {bound}, but got {actual}"
            raise HarnessAssertionError(detail, expected=f"< {bound}", actual=actual)

    @staticmethod
    def assert_lte(actual: float, bound: float, msg: Optional[str] = None) -> None:
        """Assert that actual <= bound."""
        if not (actual <= bound):
            detail = msg or f"Expected value <= {bound}, but got {actual}"
            raise HarnessAssertionError(detail, expected=f"<= {bound}", actual=actual)

    @staticmethod
    def assert_gt(actual: float, bound: float, msg: Optional[str] = None) -> None:
        """Assert that actual > bound."""
        if not (actual > bound):
            detail = msg or f"Expected value > {bound}, but got {actual}"
            raise HarnessAssertionError(detail, expected=f"> {bound}", actual=actual)
