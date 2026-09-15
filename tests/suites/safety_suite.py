"""
Safety Test Suite for ADAS ECU.
Validates fail-safe behavior under abnormal timing, safety violations, and fault conditions:
- Watchdog deadline monitoring (FR-3.1, FR-3.3, FR-3.5)
- Transition to SAFE state
- Emergency brake actuation on safety events
- Transition to FAULT state
"""

from typing import Any
from harness.assertions import Assertions
from harness.models import Priority, SystemState, TestCase, TestResult
from harness.simulators.can_simulator import BRAKE_CAN_ID
from harness.simulators.ecu_model import SimulatedECU


def test_saf_001_watchdog_deadline_violation(tc: TestCase, result: TestResult) -> None:
    """TC-SAF-001: Validate watchdog triggers SAFE state when compute exceeds 50ms (FR-3.3, FR-3.5)."""
    ecu = SimulatedECU()
    ecu.boot()
    Assertions.assert_state(ecu.state, SystemState.RUNNING, "ECU must be in RUNNING state initially")

    # Inject compute overrun: 65,000us (> 50,000us deadline)
    overrun_us = 65000
    cycle_out = ecu.process_cycle(compute_duration_us=overrun_us)

    result.actual["state_after_violation"] = ecu.state.value
    result.actual["deadline_violated"] = ecu.deadline_violated
    result.actual["brake_active"] = ecu.emergency_brake_triggered

    Assertions.assert_true(ecu.deadline_violated, "Watchdog must detect deadline violation")
    Assertions.assert_state(ecu.state, SystemState.SAFE, "ECU must enter SAFE state on deadline violation")
    Assertions.assert_true(ecu.emergency_brake_triggered, "Emergency brake must be triggered on deadline violation")

    # Verify brake CAN frame emitted
    brake_msgs = [m for m in ecu.emitted_can_frames if m.arbitration_id == BRAKE_CAN_ID]
    Assertions.assert_gt(len(brake_msgs), 0, "Emergency brake CAN frame (0x400) must be broadcast")


def test_saf_002_emergency_brake_actuation(tc: TestCase, result: TestResult) -> None:
    """TC-SAF-002: Verify explicit trigger_emergency_brake enters SAFE state (FR-3.4, NFR-3.3)."""
    ecu = SimulatedECU()
    ecu.boot()

    ecu.trigger_emergency_brake()
    result.actual["state"] = ecu.state.value
    result.actual["brake_triggered"] = ecu.emergency_brake_triggered

    Assertions.assert_state(ecu.state, SystemState.SAFE, "Emergency brake trigger must transition state to SAFE")
    Assertions.assert_true(ecu.emergency_brake_triggered, "Brake flag must be True")

    brake_msgs = [m for m in ecu.emitted_can_frames if m.arbitration_id == BRAKE_CAN_ID]
    Assertions.assert_gt(len(brake_msgs), 0, "Brake CAN message must be queued")
    Assertions.assert_equal(brake_msgs[-1].data[0], 0xFF, "Brake command payload must be 0xFF")


def test_saf_003_state_machine_transitions(tc: TestCase, result: TestResult) -> None:
    """TC-SAF-003: Validate all valid system state transitions (INIT -> RUNNING -> SAFE -> FAULT)."""
    ecu = SimulatedECU()
    Assertions.assert_state(ecu.state, SystemState.INIT, "Initial state: INIT")

    ecu.boot()
    Assertions.assert_state(ecu.state, SystemState.RUNNING, "Boot: RUNNING")

    ecu.process_cycle(compute_duration_us=55000)
    Assertions.assert_state(ecu.state, SystemState.SAFE, "Violation: SAFE")

    ecu.trigger_critical_fault()
    Assertions.assert_state(ecu.state, SystemState.FAULT, "Critical error: FAULT")

    result.actual["final_state"] = ecu.state.value


def test_saf_004_fault_state_inhibits_compute(tc: TestCase, result: TestResult) -> None:
    """TC-SAF-004: Validate that in FAULT state, nominal compute operations are inhibited."""
    ecu = SimulatedECU()
    ecu.boot()
    ecu.trigger_critical_fault()

    # Attempt to process regular cycle
    out = ecu.process_cycle(compute_duration_us=10000)
    result.actual["output"] = str(out)

    Assertions.assert_state(ecu.state, SystemState.FAULT, "ECU state must remain in FAULT")
    Assertions.assert_equal(len(ecu.sensor_queue), 0, "No processing should dequeue while in FAULT")


def register_tests(runner: Any) -> None:
    runner.register_test(
        TestCase(
            id="TC-SAF-001",
            name="Watchdog Compute Deadline Violation Handling",
            suite="safety",
            priority=Priority.CRITICAL,
            tags=["safety", "watchdog", "deadline", "regression"],
            requirement_id="FR-3.3",
            description="Verify watchdog detects >50ms compute execution and enters SAFE state with brake."
        ),
        test_saf_001_watchdog_deadline_violation
    )

    runner.register_test(
        TestCase(
            id="TC-SAF-002",
            name="Emergency Brake Actuation & Frame Broadcast",
            suite="safety",
            priority=Priority.CRITICAL,
            tags=["safety", "brake", "can", "regression"],
            requirement_id="FR-3.4",
            description="Verify emergency brake trigger commands actuator and broadcasts 0x400 frame."
        ),
        test_saf_002_emergency_brake_actuation
    )

    runner.register_test(
        TestCase(
            id="TC-SAF-003",
            name="System State Machine Transition Validation",
            suite="safety",
            priority=Priority.HIGH,
            tags=["safety", "state_machine", "regression"],
            requirement_id="NFR-3.4",
            description="Verify orderly state transitions between INIT, RUNNING, SAFE, and FAULT."
        ),
        test_saf_003_state_machine_transitions
    )

    runner.register_test(
        TestCase(
            id="TC-SAF-004",
            name="Fault State Operation Inhibition",
            suite="safety",
            priority=Priority.HIGH,
            tags=["safety", "fault", "regression"],
            requirement_id="FR-3.5",
            description="Verify unrecoverable FAULT state halts further nominal actuation."
        ),
        test_saf_004_fault_state_inhibits_compute
    )
