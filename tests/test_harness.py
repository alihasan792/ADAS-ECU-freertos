"""
Pytest Unit Tests for the ADAS ECU Automated Test Harness.
Verifies the assertion engine, CAN codec, simulated ECU algorithms, and reporting.
"""

import pytest
from harness.assertions import Assertions, HarnessAssertionError
from harness.models import SystemState, CollisionRisk, TestCase, TestResult, Priority
from harness.simulators.can_simulator import CANCodec, VirtualCANBus, LIDAR_CAN_ID, RADAR_CAN_ID, BRAKE_CAN_ID
from harness.simulators.ecu_model import SimulatedECU, SimulatedCollisionDetector, SimulatedKalmanFilter
from harness.fault_injection.injector import FaultInjector
from harness.runner import TestRunner


def test_assertions_equality():
    Assertions.assert_equal(10, 10)
    with pytest.raises(HarnessAssertionError):
        Assertions.assert_equal(10, 20)


def test_assertions_within_range():
    Assertions.assert_within_range(50.1, 50.0, 0.2)
    with pytest.raises(HarnessAssertionError):
        Assertions.assert_within_range(50.5, 50.0, 0.2)


def test_can_codec_lidar():
    msg = CANCodec.encode_lidar(12.5, -4.2)
    assert msg.arbitration_id == LIDAR_CAN_ID
    assert msg.dlc == 8
    x, y = CANCodec.decode_lidar(msg.data)
    assert pytest.approx(x, 0.01) == 12.5
    assert pytest.approx(y, 0.01) == -4.2


def test_can_codec_brake():
    msg = CANCodec.encode_brake_command()
    assert msg.arbitration_id == BRAKE_CAN_ID
    assert CANCodec.decode_brake_command(msg.data) is True


def test_collision_detector_logic():
    # Approaching critical
    info = SimulatedCollisionDetector.detect_collision(x=8.0, y=0.0, vx=-10.0, vy=0.0)
    assert info["is_approaching"] is True
    assert info["risk_level"] == CollisionRisk.CRITICAL
    assert info["should_brake"] is True


def test_ecu_watchdog_deadline_enforcement():
    ecu = SimulatedECU()
    ecu.boot()
    assert ecu.state == SystemState.RUNNING

    # Compute duration exceeding 50,000us
    out = ecu.process_cycle(compute_duration_us=55000)
    assert ecu.state == SystemState.SAFE
    assert ecu.deadline_violated is True
    assert ecu.emergency_brake_triggered is True


def test_fault_injector_payload_corruption():
    msg = CANCodec.encode_lidar(10.0, 0.0)
    corrupted = FaultInjector.inject_corrupted_payload(msg)
    assert corrupted.data != msg.data


def test_harness_runner_execution():
    runner = TestRunner()
    summary = runner.run(suite_filter="smoke")
    assert summary.total_tests == 3
    assert summary.passed_tests == 3
    assert summary.failed_tests == 0


def test_failure_evidence_capture(tmp_path):
    # Setup runner with isolated temp output dir
    runner = TestRunner(output_dir=str(tmp_path))

    # Register a deliberately failing test
    def failing_func(tc, res):
        Assertions.assert_equal(5, 99, "Deliberate failure for evidence testing")

    fail_tc = TestCase(
        id="TC-ERR-001",
        name="Deliberate Failing Test",
        suite="smoke",
        priority=Priority.HIGH,
        description="Fails to test evidence bundle"
    )
    runner.register_test(fail_tc, failing_func)

    summary = runner.run(test_id_filter="TC-ERR-001")
    assert summary.failed_tests == 1
    assert "TC-ERR-001" in summary.failed_test_ids

    # Check evidence directory
    ev_dir = tmp_path / "runs" / summary.run_id / "evidence" / "TC-ERR-001"
    assert ev_dir.exists()
    assert (ev_dir / "result.json").exists()
    assert (ev_dir / "execution.log").exists()
    assert (ev_dir / "input.json").exists()
    assert (ev_dir / "output.json").exists()

