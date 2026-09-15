"""
Physical Sensor Stimulus Generator for ADAS ECU testing.
Generates deterministic kinematic scenarios for testing Kalman filtering,
collision detection, emergency braking, and fault recovery.
"""

from dataclasses import dataclass, field
from typing import Generator, List, Optional, Tuple
import math
import time

from harness.simulators.can_simulator import CANCodec, CANMessage


@dataclass
class SensorFrame:
    """Represents a unified sensor sample matching SensorData struct in C++."""
    timestamp_us: int
    x: float = 0.0
    y: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    camera_class: int = 0
    camera_confidence: float = 0.0
    ultrasonic_distance_cm: float = 0.0
    sensor_flags: int = 0


class SensorScenarioGenerator:
    """Generates synthetic sensor data streams for test scenarios."""

    @staticmethod
    def approaching_vehicle(
        initial_distance: float = 50.0,
        relative_speed: float = -15.0,  # Approaching at 15 m/s
        duration_s: float = 3.0,
        period_s: float = 0.01  # 10ms (100 Hz)
    ) -> List[SensorFrame]:
        """Approaching target straight ahead on X axis."""
        frames: List[SensorFrame] = []
        steps = int(duration_s / period_s)
        base_time = int(time.time() * 1e6)

        for i in range(steps):
            t = i * period_s
            x = max(0.0, initial_distance + relative_speed * t)
            y = 0.0
            vx = relative_speed
            vy = 0.0

            frame = SensorFrame(
                timestamp_us=base_time + int(t * 1e6),
                x=round(x, 3),
                y=round(y, 3),
                vx=round(vx, 3),
                vy=round(vy, 3),
                camera_class=1 if x < 60.0 else 0,  # 1 = vehicle
                camera_confidence=0.92 if x < 60.0 else 0.0,
                ultrasonic_distance_cm=round(x * 100.0, 1) if x < 5.0 else 500.0,
                sensor_flags=0x03  # Lidar (0x01) + Radar (0x02)
            )
            frames.append(frame)
        return frames

    @staticmethod
    def stationary_obstacle(
        distance: float = 100.0,
        duration_s: float = 1.0,
        period_s: float = 0.01
    ) -> List[SensorFrame]:
        """Stationary target at fixed distance."""
        frames: List[SensorFrame] = []
        steps = int(duration_s / period_s)
        base_time = int(time.time() * 1e6)

        for i in range(steps):
            t = i * period_s
            frame = SensorFrame(
                timestamp_us=base_time + int(t * 1e6),
                x=distance,
                y=0.0,
                vx=0.0,
                vy=0.0,
                camera_class=3,  # 3 = obstacle
                camera_confidence=0.85,
                ultrasonic_distance_cm=distance * 100.0,
                sensor_flags=0x03
            )
            frames.append(frame)
        return frames

    @staticmethod
    def convert_frame_to_can(frame: SensorFrame) -> List[CANMessage]:
        """Converts a SensorFrame into CAN messages (Lidar + Radar)."""
        messages = [
            CANCodec.encode_lidar(frame.x, frame.y),
            CANCodec.encode_radar(frame.vx, frame.vy)
        ]
        if frame.camera_class > 0:
            messages.append(CANCodec.encode_camera(frame.camera_class, frame.camera_confidence))
        if frame.ultrasonic_distance_cm > 0:
            messages.append(CANCodec.encode_ultrasonic(frame.ultrasonic_distance_cm))
        return messages
