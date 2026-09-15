# ADAS ECU Validation & Test Harness Architecture

## 1. System Overview

The **ADAS ECU Automated Validation & Test Harness** provides a deterministic, repeatable, CLI-first testing and validation platform for the FreeRTOS-based ADAS Electronic Control Unit (ECU).

The framework implements a strict engineering loop:
```text
Stimulus  ──>  ADAS ECU Engine  ──>  Observed Output  ──>  Validation  ──>  Evidence  ──>  Report
```

---

## 2. High-Level Architecture Diagram

```text
                     ┌────────────────────────────────────┐
                     │     CLI Interface (adas-test)      │
                     │  - Batch commands (CI/CD ready)    │
                     │  - Interactive 10-Option Menu      │
                     └─────────────────┬──────────────────┘
                                       │
                                       ▼
                     ┌────────────────────────────────────┐
                     │        Test Runner Engine          │
                     │  - Suite discovery & filtering     │
                     │  - 8-stage lifecycle coordinator   │
                     │  - Timeout & process guard         │
                     └─────────────────┬──────────────────┘
                                       │
            ┌──────────────────────────┼──────────────────────────┐
            ▼                          ▼                          ▼
   ┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
   │   Test Suites   │       │ Simulators & FI │       │ Configuration   │
   │ - Smoke (3)     │       │ - Sensor Gen    │       │ - default_config│
   │ - Functional (4)│       │ - Virtual CAN   │       │ - Traceability  │
   │ - Safety (4)    │       │ - Fault Inj     │       │   Matrix (RTM)  │
   │ - CAN (4)       │       └────────┬────────┘       └─────────────────┘
   │ - Fault Inj (4) │                │
   └────────┬────────┘                │
            │                         ▼
            │               ┌───────────────────┐
            │               │  ADAS ECU Model   │
            │               │ - Kalman Filter   │
            │               │ - Collision TTC   │
            │               │ - Safety Watchdog │
            │               │ - Bounded Queues  │
            │               └─────────┬─────────┘
            │                         │
            └───────────┬─────────────┘
                        │
                        ▼
            ┌───────────────────────┐
            │   Assertion Engine    │
            │ - Tolerance checks    │
            │ - State verifications │
            │ - CAN frame asserts   │
            └───────────┬───────────┘
                        │
         ┌──────────────┴──────────────┐
         ▼                             ▼
┌──────────────────┐          ┌──────────────────┐
│ Failure Evidence │          │ Report Generator │
│ - execution.log  │          │ - Terminal ANSI  │
│ - result.json    │          │ - JSON Summary   │
│ - input.json     │          │ - JUnit XML (CI) │
│ - output.json    │          │ - HTML Dashboard │
└──────────────────┘          └──────────────────┘
```

---

## 3. Subsystem Breakdown

### 3.1 CLI & Runner Layer (`cli/adas_test.py`, `harness/runner.py`)
- **CLI Commands**:
  - `adas-test run [--suite <name>] [--all] [--test <id>] [--priority <level>] [--failed]`
  - `adas-test regression`
  - `adas-test list [--suite <name>]`
  - `adas-test report [--format json|html|junit]`
  - `adas-test interactive`
- **Standardized Exit Codes**:
  - `0`: All executed tests passed.
  - `1`: One or more tests failed.
  - `2`: Invalid CLI arguments or configuration file missing.
  - `3`: Fatal execution or harness exception.

### 3.2 Dual-Transport Simulation Layer (`harness/simulators/`)
- **CAN Simulator (`can_simulator.py`)**:
  - Encodes and decodes frames conforming strictly to `src/can_interface.cpp`:
    - `0x100`: Lidar (x, y float32)
    - `0x200`: Radar (vx, vy float32)
    - `0x250`: Camera (class uint8, confidence float32)
    - `0x300`: Ultrasonic (distance_cm float32)
    - `0x400`: Emergency brake command (0xFF byte)
- **Virtual CAN Bus (`VirtualCANBus`)**: In-memory message routing permitting complete execution without requiring Linux kernel `vcan` modules or elevated privileges.
- **Sensor Trajectory Generator (`sensor_simulator.py`)**: Produces deterministic kinematic trajectories (approaching vehicle, cut-ins, stationary obstacles).

### 3.3 Reference ECU Behavioral Engine (`ecu_model.py`)
- Replicates the FreeRTOS tasks and algorithms in deterministic Python:
  - `SimulatedKalmanFilter`: Position/velocity 4-state estimation with predict/update.
  - `SimulatedCollisionDetector`: $TTC = \frac{\text{dist}}{\text{rel\_speed}}$, warning ($TTC < 3.0$s), critical ($TTC < 1.5$s).
  - `SimulatedECU`: Queue depth bounded to 10 frames (NFR-2.3), watchdog deadline timer enforcing 50ms compute deadline (FR-3.3), transitioning state from `INIT` $\rightarrow$ `RUNNING` $\rightarrow$ `SAFE` or `FAULT`.

### 3.4 Fault Injection Subsystem (`harness/fault_injection/`)
- **CAN Timeout**: Drops frames to test watchdog and sensor timeout handling.
- **Sensor Dropout**: Simulates temporary blindness (e.g. lidar obstruction).
- **Physical Out-of-Range**: Tests negative distance sanitization.
- **Payload Corruption**: Flips bitmasks in CAN frames to test robustness without process termination.
- **Deadline Overruns**: Simulates compute loops $> 50$ms.

### 3.5 Assertion Engine (`harness/assertions.py`)
- Provides `assert_equal`, `assert_within_range`, `assert_state`, `assert_message_received`, `assert_lt`, `assert_gt`.
- Captures expected vs actual details directly into failure evidence objects upon failure.

### 3.6 Multi-Format Reporting & Failure Evidence (`harness/reporting/`)
- **Terminal Summary**: Concise table with ANSI colors, pass rate, and failure lists.
- **Machine-Readable JSON**: Full hierarchy stored in `reports/runs/<run_id>/summary.json`.
- **JUnit XML**: Standard `<testsuites>` XML stored in `reports/runs/<run_id>/junit.xml` for CI/CD test result charts.
- **Standalone HTML Dashboard**: Zero-dependency interactive web report with expandable execution logs and status badges.
- **Failure Evidence Bundles**: When any test fails, automatically generates:
  ```text
  reports/runs/<run_id>/evidence/<test_id>/
  ├── result.json
  ├── execution.log
  ├── input.json
  └── output.json
  ```
