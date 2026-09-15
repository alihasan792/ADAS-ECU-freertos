"""
CAN Communication Test Suite for ADAS ECU.
Validates:
- Message format and DLC
- Known arbitration IDs (Lidar 0x100, Radar 0x200, Camera 0x250, Ultrasonic 0x300)
- Unknown message rejection
- Brake actuation message broadcast (0x400)
"""

from typing import Any
from harness.assertions import Assertions
from harness.models import Priority, TestCase, TestResult
from harness.simulators.can_simulator import (
    BRAKE_CAN_ID, CAMERA_CAN_ID, LIDAR_CAN_ID, RADAR_CAN_ID, ULTRASONIC_CAN_ID,
    CANCodec, CANMessage, VirtualCANBus
)


def test_can_001_standard_frame_dlc(tc: TestCase, result: TestResult) -> None:
    """TC-CAN-001: Validate standard CAN frame DLC and byte layout for primary sensors (FR-1.1, FR-1.2)."""
    lidar_msg = CANCodec.encode_lidar(15.0, 2.5)
    radar_msg = CANCodec.encode_radar(-8.0, 0.0)

    result.actual["lidar_dlc"] = lidar_msg.dlc
    result.actual["radar_dlc"] = radar_msg.dlc

    Assertions.assert_equal(lidar_msg.dlc, 8, "Lidar CAN frame DLC must equal 8 bytes")
    Assertions.assert_equal(radar_msg.dlc, 8, "Radar CAN frame DLC must equal 8 bytes")
    Assertions.assert_equal(len(lidar_msg.data), 8, "Lidar payload data buffer length must be 8")
    Assertions.assert_equal(len(radar_msg.data), 8, "Radar payload data buffer length must be 8")


def test_can_002_unknown_can_id_rejection(tc: TestCase, result: TestResult) -> None:
    """TC-CAN-002: Verify arbitration IDs not in the ECU whitelist are safely ignored (NFR-2.4)."""
    bus = VirtualCANBus()
    unknown_id = 0x7FF  # Arbitrary foreign CAN ID
    bogus_msg = CANMessage(arbitration_id=unknown_id, data=b"\x00\x11\x22\x33\x44\x55\x66\x77")

    bus.send(bogus_msg)

    # Check that valid known sensor IDs were unaffected
    lidar_frames = bus.get_messages_by_id(LIDAR_CAN_ID)
    radar_frames = bus.get_messages_by_id(RADAR_CAN_ID)

    result.actual["filtered_unknown_id"] = hex(unknown_id)
    result.actual["accepted_sensor_frames"] = len(lidar_frames) + len(radar_frames)

    Assertions.assert_equal(len(lidar_frames), 0, "Unknown ID must not be interpreted as Lidar")
    Assertions.assert_equal(len(radar_frames), 0, "Unknown ID must not be interpreted as Radar")


def test_can_003_extended_sensor_parsing(tc: TestCase, result: TestResult) -> None:
    """TC-CAN-003: Validate Camera (0x250) and Ultrasonic (0x300) frame decoding."""
    camera_msg = CANCodec.encode_camera(object_class=2, confidence=0.88)  # 2 = Pedestrian
    ultra_msg = CANCodec.encode_ultrasonic(distance_cm=142.5)

    Assertions.assert_equal(camera_msg.arbitration_id, CAMERA_CAN_ID, "Camera ID must be 0x250")
    Assertions.assert_equal(ultra_msg.arbitration_id, ULTRASONIC_CAN_ID, "Ultrasonic ID must be 0x300")

    cls_out, conf_out = CANCodec.decode_camera(camera_msg.data)
    dist_out = CANCodec.decode_ultrasonic(ultra_msg.data)

    result.actual["camera"] = {"class": cls_out, "confidence": round(conf_out, 2)}
    result.actual["ultrasonic_distance_cm"] = round(dist_out, 1)

    Assertions.assert_equal(cls_out, 2, "Camera object class decoded correctly as pedestrian")
    Assertions.assert_within_range(conf_out, 0.88, 0.01, "Camera confidence decoded correctly")
    Assertions.assert_within_range(dist_out, 142.5, 0.1, "Ultrasonic distance decoded correctly")


def test_can_004_brake_frame_broadcast(tc: TestCase, result: TestResult) -> None:
    """TC-CAN-004: Validate emergency brake CAN command (ID 0x400, DLC 1, payload 0xFF) (NFR-3.3)."""
    brake_msg = CANCodec.encode_brake_command()
    result.actual["brake_can_id"] = hex(brake_msg.arbitration_id)
    result.actual["brake_dlc"] = brake_msg.dlc
    result.actual["payload_hex"] = brake_msg.data.hex().upper()

    Assertions.assert_equal(brake_msg.arbitration_id, BRAKE_CAN_ID, "Brake CAN ID must be 0x400")
    Assertions.assert_equal(brake_msg.dlc, 1, "Brake command DLC must be 1 byte")
    Assertions.assert_equal(brake_msg.data[0], 0xFF, "Brake actuation command payload must be 0xFF")


def register_tests(runner: Any) -> None:
    runner.register_test(
        TestCase(
            id="TC-CAN-001",
            name="Standard CAN Frame Structure & DLC Verification",
            suite="can",
            priority=Priority.HIGH,
            tags=["can", "format", "dlc", "regression"],
            requirement_id="FR-1.1",
            description="Validate byte packing, payload lengths, and DLC for standard sensor CAN frames."
        ),
        test_can_001_standard_frame_dlc
    )

    runner.register_test(
        TestCase(
            id="TC-CAN-002",
            name="Unknown CAN Arbitration ID Filtering",
            suite="can",
            priority=Priority.MEDIUM,
            tags=["can", "filter", "robustness"],
            requirement_id="NFR-2.4",
            description="Verify unmapped CAN arbitration IDs are dropped without disrupting sensor processing."
        ),
        test_can_002_unknown_can_id_rejection
    )

    runner.register_test(
        TestCase(
            id="TC-CAN-003",
            name="Extended Sensor CAN Frames Parsing",
            suite="can",
            priority=Priority.MEDIUM,
            tags=["can", "camera", "ultrasonic"],
            requirement_id="FR-1.4",
            description="Verify Camera (0x250) and Ultrasonic (0x300) message formats and unit decoding."
        ),
        test_can_003_extended_sensor_parsing
    )

    runner.register_test(
        TestCase(
            id="TC-CAN-004",
            name="Emergency Brake Broadcast Frame Layout",
            suite="can",
            priority=Priority.CRITICAL,
            tags=["can", "brake", "safety", "regression"],
            requirement_id="NFR-3.3",
            description="Verify emergency brake actuation broadcast frame ID 0x400 with 0xFF byte."
        ),
        test_can_004_brake_frame_broadcast
    )
