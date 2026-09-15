"""
Fault Injection Engine for ADAS ECU Automated Test Harness.
Injects controlled sensor, CAN, and timing anomalies to validate ECU fault-tolerance and fail-safe behavior.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
import copy
import struct

from harness.simulators.can_simulator import CANMessage


class FaultType(str, Enum):
    CAN_TIMEOUT = "CAN_TIMEOUT"
    SENSOR_DROPOUT = "SENSOR_DROPOUT"
    OUT_OF_RANGE = "OUT_OF_RANGE"
    CORRUPTED_PAYLOAD = "CORRUPTED_PAYLOAD"
    DEADLINE_OVERRUN = "DEADLINE_OVERRUN"


class FaultInjector:
    """Manages controlled fault injections into test scenarios."""

    @staticmethod
    def inject_can_timeout(messages: List[CANMessage], target_can_id: int) -> List[CANMessage]:
        """Simulates CAN timeout by dropping all frames with target_can_id."""
        return [m for m in messages if m.arbitration_id != target_can_id]

    @staticmethod
    def inject_sensor_dropout(
        sensor_frames: List[Dict[str, Any]],
        start_index: int,
        drop_count: int
    ) -> List[Dict[str, Any]]:
        """Simulates temporary sensor blackout by omitting a range of frames."""
        modified = copy.deepcopy(sensor_frames)
        end_index = min(len(modified), start_index + drop_count)
        del modified[start_index:end_index]
        return modified

    @staticmethod
    def inject_out_of_range(sensor_data: Dict[str, Any], field: str = "x", value: float = -999.0) -> Dict[str, Any]:
        """Injects impossible physical values (e.g. negative distance or warp speed)."""
        modified = copy.deepcopy(sensor_data)
        modified[field] = value
        return modified

    @staticmethod
    def inject_corrupted_payload(message: CANMessage) -> CANMessage:
        """Flips/mutates bytes in a CAN message payload."""
        if not message.data:
            return message
        data_bytearray = bytearray(message.data)
        data_bytearray[0] ^= 0xFF  # Flip bits in first byte
        return CANMessage(
            arbitration_id=message.arbitration_id,
            data=bytes(data_bytearray),
            dlc=message.dlc,
            is_extended_id=message.is_extended_id,
            is_fd=message.is_fd
        )

    @staticmethod
    def inject_compute_deadline_overrun(nominal_duration_us: int = 15000, overrun_us: int = 60000) -> int:
        """Returns compute duration exceeding the 50,000us (50ms) task deadline."""
        return overrun_us
