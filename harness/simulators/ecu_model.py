"""
Reference Behavioral Model of the ADAS ECU.
Matches the exact algorithms implemented in C++ (kalman.cpp, collision_detection.cpp,
safety.cpp, task_watchdog.cpp, and can_interface.cpp).
Allows fast, cross-platform, deterministic verification of ADAS logic.
"""

from typing import Any, Dict, List, Optional, Tuple
import math
import time

from harness.models import SystemState, CollisionRisk
from harness.simulators.can_simulator import CANCodec, CANMessage, BRAKE_CAN_ID


class SimulatedKalmanFilter:
    """4-state Kalman Filter [x, y, vx, vy] identical to src/kalman.cpp."""
    def __init__(self):
        self.x = 0.0
        self.y = 0.0
        self.vx = 0.0
        self.vy = 0.0
        self.initialized = False
        self.last_timestamp_us = 0

    def initialize(self, x: float, y: float, vx: float = 0.0, vy: float = 0.0, timestamp_us: int = 0) -> None:
        self.x = float(x)
        self.y = float(y)
        self.vx = float(vx)
        self.vy = float(vy)
        self.initialized = True
        self.last_timestamp_us = timestamp_us

    def predict(self, dt_sec: float) -> None:
        if not self.initialized or dt_sec <= 0.0:
            return
        self.x += self.vx * dt_sec
        self.y += self.vy * dt_sec

    def update(self, meas_x: Optional[float] = None, meas_y: Optional[float] = None,
               meas_vx: Optional[float] = None, meas_vy: Optional[float] = None) -> None:
        if not self.initialized:
            self.initialize(
                meas_x if meas_x is not None else 0.0,
                meas_y if meas_y is not None else 0.0,
                meas_vx if meas_vx is not None else 0.0,
                meas_vy if meas_vy is not None else 0.0
            )
            return

        # Simple weighted Kalman update matching C++ steady-state gains
        alpha = 0.8
        if meas_x is not None:
            self.x = (1.0 - alpha) * self.x + alpha * meas_x
        if meas_y is not None:
            self.y = (1.0 - alpha) * self.y + alpha * meas_y
        if meas_vx is not None:
            self.vx = (1.0 - alpha) * self.vx + alpha * meas_vx
        if meas_vy is not None:
            self.vy = (1.0 - alpha) * self.vy + alpha * meas_vy

    def get_state(self) -> Dict[str, float]:
        return {
            "x": round(self.x, 3),
            "y": round(self.y, 3),
            "vx": round(self.vx, 3),
            "vy": round(self.vy, 3)
        }


class SimulatedCollisionDetector:
    """Collision detector matching src/collision_detection.cpp."""
    WARNING_TTC_SEC = 3.0
    CRITICAL_TTC_SEC = 1.5
    CRITICAL_DISTANCE_M = 10.0

    @classmethod
    def detect_collision(cls, x: float, y: float, vx: float, vy: float) -> Dict[str, Any]:
        distance = math.sqrt(x * x + y * y)
        dot_product = x * vx + y * vy
        is_approaching = dot_product < -1e-4

        if is_approaching and distance > 1e-4:
            relative_speed = -dot_product / distance
            ttc = distance / relative_speed if relative_speed > 1e-4 else float("inf")
        else:
            relative_speed = 0.0
            ttc = float("inf")

        risk_level = CollisionRisk.NONE
        if ttc < cls.CRITICAL_TTC_SEC or distance < cls.CRITICAL_DISTANCE_M:
            risk_level = CollisionRisk.CRITICAL
        elif ttc < cls.WARNING_TTC_SEC:
            risk_level = CollisionRisk.WARNING

        return {
            "distance": round(distance, 3),
            "relative_speed": round(relative_speed, 3),
            "time_to_collision": round(ttc, 3),
            "is_approaching": is_approaching,
            "risk_level": risk_level,
            "should_brake": risk_level == CollisionRisk.CRITICAL
        }


class SimulatedECU:
    """Full behavioral ECU environment with FreeRTOS queue simulation and safety watchdog."""
    MAX_QUEUE_DEPTH = 10

    def __init__(self):
        self.state = SystemState.INIT
        self.kalman = SimulatedKalmanFilter()
        self.sensor_queue: List[Dict[str, Any]] = []
        self.dropped_queue_frames = 0
        self.deadline_violated = False
        self.emergency_brake_triggered = False
        self.emitted_can_frames: List[CANMessage] = []
        self.logs: List[str] = []

    def log(self, message: str) -> None:
        ts = datetime_str = time.strftime("%H:%M:%S", time.localtime())
        self.logs.append(f"[{ts}] {message}")

    def boot(self) -> None:
        self.state = SystemState.INIT
        self.log("ECU Boot: Initializing queues and state")
        # Watchdog advances state to RUNNING upon first execution cycle
        self.state = SystemState.RUNNING
        self.log("ECU Watchdog: Transitioned state to RUNNING")

    def enqueue_sensor_data(self, data: Dict[str, Any]) -> bool:
        if len(self.sensor_queue) >= self.MAX_QUEUE_DEPTH:
            self.dropped_queue_frames += 1
            self.log("[SENSOR] Queue full (depth=10), dropping frame")
            return False
        self.sensor_queue.append(data)
        return True

    def process_cycle(self, compute_duration_us: int = 15000) -> Dict[str, Any]:
        """Runs one cycle of compute task and watchdog check."""
        if self.state == SystemState.FAULT:
            self.log("[COMPUTE] ECU in FAULT state; compute inhibited")
            return {"state": self.state}

        # 1. Watchdog deadline check (Deadline = 50ms = 50,000us)
        if compute_duration_us > 50000:
            self.deadline_violated = True
            self.state = SystemState.SAFE
            self.emergency_brake_triggered = True
            self.emitted_can_frames.append(CANCodec.encode_brake_command())
            self.log(f"[WATCHDOG] ⚠️ DEADLINE VIOLATED ({compute_duration_us}us > 50000us). Entered SAFE state. Brake commanded.")
            return {"state": self.state, "deadline_violated": True, "brake": True}

        # 2. Dequeue sensor data
        meas = self.sensor_queue.pop(0) if self.sensor_queue else None

        # 3. Kalman update
        if meas:
            self.kalman.predict(dt_sec=0.02)  # 20ms period
            self.kalman.update(
                meas_x=meas.get("x"),
                meas_y=meas.get("y"),
                meas_vx=meas.get("vx"),
                meas_vy=meas.get("vy")
            )

        st = self.kalman.get_state()

        # 4. Collision check
        col = SimulatedCollisionDetector.detect_collision(st["x"], st["y"], st["vx"], st["vy"])

        # 5. Actuation if critical collision
        if col["should_brake"]:
            self.emergency_brake_triggered = True
            self.emitted_can_frames.append(CANCodec.encode_brake_command())
            self.log(f"[COMPUTE] ⚠️ CRITICAL COLLISION! TTC={col['time_to_collision']}s. Emergency brake activated.")

        return {
            "state": self.state,
            "kalman_state": st,
            "collision": col,
            "deadline_violated": self.deadline_violated,
            "brake_active": self.emergency_brake_triggered
        }

    def trigger_emergency_brake(self) -> None:
        self.emergency_brake_triggered = True
        self.state = SystemState.SAFE
        self.emitted_can_frames.append(CANCodec.encode_brake_command())
        self.log("[SAFETY] Emergency brake manually triggered -> entered SAFE state")

    def trigger_critical_fault(self) -> None:
        self.state = SystemState.FAULT
        self.emergency_brake_triggered = True
        self.emitted_can_frames.append(CANCodec.encode_brake_command())
        self.log("[SAFETY] Critical hardware/bus error -> entered FAULT state")
