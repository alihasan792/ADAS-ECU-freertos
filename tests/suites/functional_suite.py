"""
Functional Test Suite for ADAS ECU.
Validates normal ADAS operational behavior:
- Kalman filter state estimation and velocity tracking
- Collision detection warning and critical TTC computation
- Multi-sensor fusion tracking
"""

from typing import Any
from harness.assertions import Assertions
from harness.models import CollisionRisk, Priority, TestCase, TestResult
from harness.simulators.ecu_model import SimulatedCollisionDetector, SimulatedECU, SimulatedKalmanFilter
from harness.simulators.sensor_simulator import SensorScenarioGenerator


def test_fun_001_kalman_convergence(tc: TestCase, result: TestResult) -> None:
    """TC-FUN-001: Validate Kalman filter convergence on approaching target (FR-2.1, FR-2.2)."""
    kf = SimulatedKalmanFilter()
    kf.initialize(x=50.0, y=0.0, vx=-10.0, vy=0.0)

    # Simulate 50 cycles (1 second at 50Hz)
    dt = 0.02
    current_x = 50.0
    vx_true = -10.0

    for i in range(50):
        current_x += vx_true * dt
        kf.predict(dt)
        # Add slight measurement noise
        meas_x = current_x + (0.1 if i % 2 == 0 else -0.1)
        kf.update(meas_x=meas_x, meas_vx=vx_true)

    state = kf.get_state()
    result.actual["final_state"] = state
    result.actual["expected_x"] = round(current_x, 3)

    Assertions.assert_within_range(state["x"], current_x, 0.5, "Kalman position should track true trajectory within 0.5m")
    Assertions.assert_within_range(state["vx"], vx_true, 0.5, "Kalman velocity should track within 0.5 m/s")


def test_fun_002_collision_warning(tc: TestCase, result: TestResult) -> None:
    """TC-FUN-002: Verify collision warning trigger when TTC < 3.0 seconds."""
    # Target approaching: x=25m, vx=-10m/s -> TTC = 2.5s
    info = SimulatedCollisionDetector.detect_collision(x=25.0, y=0.0, vx=-10.0, vy=0.0)
    result.actual["collision_info"] = info

    Assertions.assert_true(info["is_approaching"], "Object moving toward vehicle must be flagged as approaching")
    Assertions.assert_within_range(info["time_to_collision"], 2.5, 0.05, "TTC must be exactly 2.5s")
    Assertions.assert_equal(info["risk_level"], CollisionRisk.WARNING, "Risk level must be WARNING when 1.5s <= TTC < 3.0s")
    Assertions.assert_false(info["should_brake"], "Warning level should not command emergency braking")


def test_fun_003_collision_critical_brake(tc: TestCase, result: TestResult) -> None:
    """TC-FUN-003: Verify critical emergency brake trigger when TTC < 1.5 seconds (NFR-3.3)."""
    # Target close and fast: x=12m, vx=-12m/s -> TTC = 1.0s
    info = SimulatedCollisionDetector.detect_collision(x=12.0, y=0.0, vx=-12.0, vy=0.0)
    result.actual["collision_info"] = info

    Assertions.assert_true(info["is_approaching"], "Target must be approaching")
    Assertions.assert_lt(info["time_to_collision"], 1.5, "TTC must be < 1.5s")
    Assertions.assert_equal(info["risk_level"], CollisionRisk.CRITICAL, "Risk level must be CRITICAL")
    Assertions.assert_true(info["should_brake"], "Critical risk must immediately command emergency brake")


def test_fun_004_multi_sensor_fusion(tc: TestCase, result: TestResult) -> None:
    """TC-FUN-004: Validate multi-sensor fusion frame composition (Lidar, Radar, Camera, Ultrasonic)."""
    frames = SensorScenarioGenerator.approaching_vehicle(initial_distance=30.0, relative_speed=-10.0, duration_s=0.1)
    Assertions.assert_gt(len(frames), 0, "Scenario generator must produce frames")

    sample_frame = frames[0]
    result.actual["sensor_frame"] = {
        "x": sample_frame.x,
        "vx": sample_frame.vx,
        "camera_class": sample_frame.camera_class,
        "camera_confidence": sample_frame.camera_confidence
    }

    Assertions.assert_gt(sample_frame.x, 0.0, "Object distance must be positive")
    Assertions.assert_equal(sample_frame.camera_class, 1, "Detected camera object class should be vehicle (1)")
    Assertions.assert_gt(sample_frame.camera_confidence, 0.9, "Camera confidence should be > 0.9")


def register_tests(runner: Any) -> None:
    runner.register_test(
        TestCase(
            id="TC-FUN-001",
            name="Kalman Filter State Estimation Convergence",
            suite="functional",
            priority=Priority.HIGH,
            tags=["functional", "kalman", "fusion", "regression"],
            requirement_id="FR-2.1",
            description="Verify Kalman filter accurately tracks position and velocity during constant approach."
        ),
        test_fun_001_kalman_convergence
    )

    runner.register_test(
        TestCase(
            id="TC-FUN-002",
            name="Collision Detector Warning Threshold Trigger",
            suite="functional",
            priority=Priority.HIGH,
            tags=["functional", "collision", "ttc", "regression"],
            requirement_id="FR-3.1",
            description="Verify collision warning activates when Time-to-Collision is below 3.0 seconds."
        ),
        test_fun_002_collision_warning
    )

    runner.register_test(
        TestCase(
            id="TC-FUN-003",
            name="Collision Critical Emergency Brake Actuation",
            suite="functional",
            priority=Priority.CRITICAL,
            tags=["functional", "safety", "brake", "regression"],
            requirement_id="NFR-3.3",
            description="Verify emergency brake trigger fires when TTC < 1.5 seconds."
        ),
        test_fun_003_collision_critical_brake
    )

    runner.register_test(
        TestCase(
            id="TC-FUN-004",
            name="Multi-Sensor Fusion Data Composition",
            suite="functional",
            priority=Priority.MEDIUM,
            tags=["functional", "sensor", "fusion"],
            requirement_id="FR-1.4",
            description="Verify synchronized integration of Lidar, Radar, and Camera attributes."
        ),
        test_fun_004_multi_sensor_fusion
    )
