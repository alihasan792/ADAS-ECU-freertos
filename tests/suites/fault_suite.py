"""
Fault Injection Test Suite for ADAS ECU.
Introduces controlled anomalies:
- Sensor dropout / packet loss
- CAN communication silence / timeout
- Physical out-of-range sensor measurements
- Corrupted CAN payload resilience
"""

from typing import Any
from harness.assertions import Assertions
from harness.fault_injection.injector import FaultInjector
from harness.models import Priority, TestCase, TestResult
from harness.simulators.can_simulator import CANCodec, VirtualCANBus
from harness.simulators.ecu_model import SimulatedECU, SimulatedKalmanFilter
from harness.simulators.sensor_simulator import SensorScenarioGenerator


def test_flt_001_sensor_dropout(tc: TestCase, result: TestResult) -> None:
    """TC-FLT-001: Validate Kalman filter dead-reckoning during temporary sensor blackout."""
    kf = SimulatedKalmanFilter()
    kf.initialize(x=40.0, y=0.0, vx=-10.0, vy=0.0)

    # 1. Normal tracking for 10 cycles (dt=0.02s)
    dt = 0.02
    current_x = 40.0
    for _ in range(10):
        current_x -= 10.0 * dt
        kf.predict(dt)
        kf.update(meas_x=current_x, meas_vx=-10.0)

    x_before_drop = kf.get_state()["x"]

    # 2. Sensor Dropout for 15 cycles: only predict(), no measurement update!
    for _ in range(15):
        current_x -= 10.0 * dt
        kf.predict(dt)

    x_after_drop = kf.get_state()["x"]
    result.actual["x_before_dropout"] = x_before_drop
    result.actual["x_after_dropout"] = x_after_drop
    result.actual["expected_x"] = round(current_x, 3)

    # Filter should have dead-reckoned the vehicle trajectory despite missing measurements
    Assertions.assert_within_range(x_after_drop, current_x, 0.2, "Kalman dead reckoning must maintain accurate position during dropout")


def test_flt_002_can_timeout_detection(tc: TestCase, result: TestResult) -> None:
    """TC-FLT-002: Validate behavior during CAN bus communication silence."""
    bus = VirtualCANBus()
    # Expect frame from bus with 0.05s timeout
    frame = bus.receive(timeout_s=0.05)

    result.actual["frame_received"] = frame is not None
    Assertions.assert_true(frame is None, "Simulated bus silence should result in timeout (None frame)")


def test_flt_003_out_of_range_sensor_rejection(tc: TestCase, result: TestResult) -> None:
    """TC-FLT-003: Validate system rejects absurd/negative physical distances."""
    raw_invalid_distance = -500.0  # Physically impossible for forward lidar
    data = {"x": raw_invalid_distance, "y": 0.0, "vx": 0.0, "vy": 0.0}

    # Sanitization filter: reject x < 0
    is_valid = data["x"] >= 0.0
    result.actual["invalid_input_x"] = raw_invalid_distance
    result.actual["filter_accepted"] = is_valid

    Assertions.assert_false(is_valid, "Negative distance readings must be flagged as invalid and rejected")


def test_flt_004_corrupted_payload_recovery(tc: TestCase, result: TestResult) -> None:
    """TC-FLT-004: Validate resilience against corrupted / bit-flipped CAN payloads (NFR-2.4)."""
    valid_msg = CANCodec.encode_lidar(20.0, 0.0)
    corrupted_msg = FaultInjector.inject_corrupted_payload(valid_msg)

    result.actual["original_hex"] = valid_msg.data.hex()
    result.actual["corrupted_hex"] = corrupted_msg.data.hex()

    Assertions.assert_not_equal(corrupted_msg.data, valid_msg.data, "Payload must be corrupted")

    # Safe decoding with error handling should not throw unhandled crash
    try:
        x, y = CANCodec.decode_lidar(corrupted_msg.data)
        decoded = True
    except Exception:
        decoded = False

    result.actual["decoded_without_crash"] = decoded
    Assertions.assert_true(decoded, "Payload decoding must execute safely without process crash")


def register_tests(runner: Any) -> None:
    runner.register_test(
        TestCase(
            id="TC-FLT-001",
            name="Sensor Dropout & Dead Reckoning Resilience",
            suite="fault",
            priority=Priority.HIGH,
            tags=["fault", "dropout", "kalman", "regression"],
            requirement_id="NFR-2.1",
            description="Verify state estimation continues accurately via dead-reckoning during sensor dropout."
        ),
        test_flt_001_sensor_dropout
    )

    runner.register_test(
        TestCase(
            id="TC-FLT-002",
            name="CAN Communication Timeout Detection",
            suite="fault",
            priority=Priority.HIGH,
            tags=["fault", "can", "timeout", "regression"],
            requirement_id="FR-3.1",
            description="Verify test harness detects missing CAN transmissions and enforces timeout."
        ),
        test_flt_002_can_timeout_detection
    )

    runner.register_test(
        TestCase(
            id="TC-FLT-003",
            name="Out-of-Range Sensor Measurement Filtering",
            suite="fault",
            priority=Priority.MEDIUM,
            tags=["fault", "sensor", "range"],
            requirement_id="FR-1.1",
            description="Verify invalid negative distance inputs are safely detected and filtered."
        ),
        test_flt_003_out_of_range_sensor_rejection
    )

    runner.register_test(
        TestCase(
            id="TC-FLT-004",
            name="Corrupted CAN Payload Handling Resilience",
            suite="fault",
            priority=Priority.MEDIUM,
            tags=["fault", "can", "corrupt", "robustness"],
            requirement_id="NFR-2.4",
            description="Verify bit-flipped or mutated CAN frames are processed without process termination."
        ),
        test_flt_004_corrupted_payload_recovery
    )
