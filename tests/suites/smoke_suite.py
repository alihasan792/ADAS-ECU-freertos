"""
Smoke Test Suite for ADAS ECU.
Quickly determines whether the system is functioning at a basic level:
- ECU boot & state initialization
- CAN sensor payload unpacking
- Bounded queue capacity & memory safety
"""

from typing import Any
from harness.assertions import Assertions
from harness.models import Priority, SystemState, TestCase, TestResult
from harness.simulators.can_simulator import CANCodec, LIDAR_CAN_ID, RADAR_CAN_ID
from harness.simulators.ecu_model import SimulatedECU


def test_smk_001_ecu_init(tc: TestCase, result: TestResult) -> None:
    """TC-SMK-001: Validate ECU boot & state machine initialization."""
    ecu = SimulatedECU()
    result.actual["initial_state"] = ecu.state.value

    # Pre-boot state must be INIT
    Assertions.assert_state(ecu.state, SystemState.INIT, "Initial state must be INIT")

    # Boot the ECU
    ecu.boot()
    result.actual["booted_state"] = ecu.state.value

    # System state should transition to RUNNING
    Assertions.assert_state(ecu.state, SystemState.RUNNING, "ECU state must advance to RUNNING after boot")
    Assertions.assert_equal(len(ecu.sensor_queue), 0, "Sensor queue should be empty upon boot")


def test_smk_002_sensor_can_decode(tc: TestCase, result: TestResult) -> None:
    """TC-SMK-002: Validate basic Lidar and Radar CAN frame parsing."""
    test_x, test_y = 25.5, -3.2
    test_vx, test_vy = -12.0, 0.5

    lidar_msg = CANCodec.encode_lidar(test_x, test_y)
    radar_msg = CANCodec.encode_radar(test_vx, test_vy)

    Assertions.assert_equal(lidar_msg.arbitration_id, LIDAR_CAN_ID, "Lidar CAN ID must be 0x100")
    Assertions.assert_equal(lidar_msg.dlc, 8, "Lidar DLC must be 8 bytes")
    Assertions.assert_equal(radar_msg.arbitration_id, RADAR_CAN_ID, "Radar CAN ID must be 0x200")
    Assertions.assert_equal(radar_msg.dlc, 8, "Radar DLC must be 8 bytes")

    decoded_x, decoded_y = CANCodec.decode_lidar(lidar_msg.data)
    decoded_vx, decoded_vy = CANCodec.decode_radar(radar_msg.data)

    result.actual["decoded_lidar"] = {"x": decoded_x, "y": decoded_y}
    result.actual["decoded_radar"] = {"vx": decoded_vx, "vy": decoded_vy}

    Assertions.assert_within_range(decoded_x, test_x, 0.001, "Lidar X decoded correctly")
    Assertions.assert_within_range(decoded_y, test_y, 0.001, "Lidar Y decoded correctly")
    Assertions.assert_within_range(decoded_vx, test_vx, 0.001, "Radar Vx decoded correctly")
    Assertions.assert_within_range(decoded_vy, test_vy, 0.001, "Radar Vy decoded correctly")


def test_smk_003_queue_overflow(tc: TestCase, result: TestResult) -> None:
    """TC-SMK-003: Verify bounded sensor queue enforcement (NFR-2.3: max depth 10, no crash)."""
    ecu = SimulatedECU()
    ecu.boot()

    # Enqueue 10 valid elements
    for i in range(10):
        ok = ecu.enqueue_sensor_data({"x": float(i), "y": 0.0, "vx": 0.0, "vy": 0.0})
        Assertions.assert_true(ok, f"Queue insertion {i+1}/10 must succeed")

    Assertions.assert_equal(len(ecu.sensor_queue), 10, "Queue depth must be exactly 10")

    # Enqueue 11th element: must be safely rejected without crash
    overflow_ok = ecu.enqueue_sensor_data({"x": 99.0, "y": 0.0, "vx": 0.0, "vy": 0.0})
    result.actual["queue_depth"] = len(ecu.sensor_queue)
    result.actual["overflow_accepted"] = overflow_ok
    result.actual["dropped_count"] = ecu.dropped_queue_frames

    Assertions.assert_false(overflow_ok, "11th element must be dropped on bounded queue")
    Assertions.assert_equal(len(ecu.sensor_queue), 10, "Queue depth must remain bounded at 10")
    Assertions.assert_equal(ecu.dropped_queue_frames, 1, "Dropped frames counter must increment")


def register_tests(runner: Any) -> None:
    runner.register_test(
        TestCase(
            id="TC-SMK-001",
            name="ECU Initialization & State Verification",
            suite="smoke",
            priority=Priority.CRITICAL,
            tags=["smoke", "init", "state", "regression"],
            requirement_id="NFR-3.4",
            description="Verify ECU boots cleanly, transitions to RUNNING, and initializes queues."
        ),
        test_smk_001_ecu_init
    )

    runner.register_test(
        TestCase(
            id="TC-SMK-002",
            name="Basic CAN Sensor Frame Decoding",
            suite="smoke",
            priority=Priority.HIGH,
            tags=["smoke", "can", "sensor", "regression"],
            requirement_id="FR-1.1",
            description="Verify Lidar and Radar CAN frames are correctly structured and decoded."
        ),
        test_smk_002_sensor_can_decode
    )

    runner.register_test(
        TestCase(
            id="TC-SMK-003",
            name="Sensor Queue Bounded Capacity",
            suite="smoke",
            priority=Priority.HIGH,
            tags=["smoke", "queue", "reliability", "regression"],
            requirement_id="NFR-2.3",
            description="Verify sensor queue depth is strictly bounded at 10 and safely drops excess frames."
        ),
        test_smk_003_queue_overflow
    )
