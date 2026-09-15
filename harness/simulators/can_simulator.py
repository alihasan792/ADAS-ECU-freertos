"""
CAN & CAN-FD Frame Simulator and Virtual Bus.
Strictly models the CAN frame byte-level formats defined in the C++ ECU codebase:
- LIDAR_CAN_ID = 0x100 (256): [x_float, y_float]
- RADAR_CAN_ID = 0x200 (512): [vx_float, vy_float]
- CAMERA_CAN_ID = 0x250 (592): [class_byte, confidence_float]
- ULTRASONIC_CAN_ID = 0x300 (768): [distance_cm_float]
- BRAKE_CAN_ID = 0x400 (1024): [0xFF]
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
import struct
import time


LIDAR_CAN_ID = 0x100
RADAR_CAN_ID = 0x200
CAMERA_CAN_ID = 0x250
ULTRASONIC_CAN_ID = 0x300
BRAKE_CAN_ID = 0x400


@dataclass
class CANMessage:
    """Represents a standardized CAN/CAN-FD frame."""
    arbitration_id: int
    data: bytes
    dlc: int = 8
    is_extended_id: bool = False
    is_fd: bool = False
    timestamp: float = field(default_factory=time.time)

    def __repr__(self) -> str:
        data_hex = " ".join(f"{b:02X}" for b in self.data)
        return f"<CANMessage ID=0x{self.arbitration_id:X} DLC={self.dlc} Data=[{data_hex}]>"


class CANCodec:
    """Encodes and decodes physical engineering units to/from CAN frame payloads."""

    @staticmethod
    def encode_lidar(x: float, y: float) -> CANMessage:
        data = struct.pack("<ff", float(x), float(y))
        return CANMessage(arbitration_id=LIDAR_CAN_ID, data=data, dlc=len(data))

    @staticmethod
    def decode_lidar(data: bytes) -> Tuple[float, float]:
        if len(data) < 8:
            raise ValueError(f"Lidar frame requires at least 8 bytes, got {len(data)}")
        x, y = struct.unpack("<ff", data[:8])
        return x, y

    @staticmethod
    def encode_radar(vx: float, vy: float) -> CANMessage:
        data = struct.pack("<ff", float(vx), float(vy))
        return CANMessage(arbitration_id=RADAR_CAN_ID, data=data, dlc=len(data))

    @staticmethod
    def decode_radar(data: bytes) -> Tuple[float, float]:
        if len(data) < 8:
            raise ValueError(f"Radar frame requires at least 8 bytes, got {len(data)}")
        vx, vy = struct.unpack("<ff", data[:8])
        return vx, vy

    @staticmethod
    def encode_camera(object_class: int, confidence: float) -> CANMessage:
        # 1 byte class + 4 bytes confidence + 3 bytes padding
        data = struct.pack("<Bfxxx", object_class, float(confidence))
        return CANMessage(arbitration_id=CAMERA_CAN_ID, data=data, dlc=len(data))

    @staticmethod
    def decode_camera(data: bytes) -> Tuple[int, float]:
        if len(data) < 5:
            raise ValueError(f"Camera frame requires at least 5 bytes, got {len(data)}")
        obj_class, conf = struct.unpack("<Bf", data[:5])
        return obj_class, conf

    @staticmethod
    def encode_ultrasonic(distance_cm: float) -> CANMessage:
        # 4 bytes float + 4 bytes padding
        data = struct.pack("<fxxxx", float(distance_cm))
        return CANMessage(arbitration_id=ULTRASONIC_CAN_ID, data=data, dlc=len(data))

    @staticmethod
    def decode_ultrasonic(data: bytes) -> float:
        if len(data) < 4:
            raise ValueError(f"Ultrasonic frame requires at least 4 bytes, got {len(data)}")
        (dist_cm,) = struct.unpack("<f", data[:4])
        return dist_cm

    @staticmethod
    def encode_brake_command() -> CANMessage:
        return CANMessage(arbitration_id=BRAKE_CAN_ID, data=bytes([0xFF]), dlc=1)

    @staticmethod
    def decode_brake_command(data: bytes) -> bool:
        if len(data) >= 1 and data[0] == 0xFF:
            return True
        return False


class VirtualCANBus:
    """
    In-memory virtual CAN bus supporting non-blocking transmission,
    filtered reception, and simulated bus delays without OS kernel privileges.
    """
    def __init__(self, channel: str = "vcan0"):
        self.channel = channel
        self.history: List[CANMessage] = []
        self._listeners: List[Any] = []
        self.is_connected = True

    def send(self, message: CANMessage) -> bool:
        if not self.is_connected:
            return False
        self.history.append(message)
        return True

    def receive(self, timeout_s: float = 0.1, filter_id: Optional[int] = None) -> Optional[CANMessage]:
        start = time.time()
        while time.time() - start < timeout_s:
            for msg in reversed(self.history):
                if filter_id is None or msg.arbitration_id == filter_id:
                    return msg
            time.sleep(0.005)
        return None

    def get_messages_by_id(self, can_id: int) -> List[CANMessage]:
        return [msg for msg in self.history if msg.arbitration_id == can_id]

    def clear(self) -> None:
        self.history.clear()

    def shutdown(self) -> None:
        self.is_connected = False
