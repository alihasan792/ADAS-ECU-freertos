# ADAS ECU Automated Testing & Validation Strategy

## 1. Testing Philosophy

The ADAS ECU Automated Validation & Test Harness follows the automotive V-Model testing hierarchy:

```text
Requirements (requirements.md)             Automated Test Suites (tests/suites/)
       │                                                    ▲
       ├── System Requirements (FR-3, NFR-3) ───────────────┤ Safety & Fault Suites
       │                                                    │
       ├── Functional Requirements (FR-1, FR-2) ────────────┤ Functional & CAN Suites
       │                                                    │
       └── Non-Functional / Smoke (NFR-1, NFR-2) ───────────┘ Smoke Suite & CTest Units
```

Every automated test case must answer five core engineering questions:
1. **What stimulus was injected?** (Sensor trajectory, CAN frame, or fault condition)
2. **What behavior was expected?** (State transition, Kalman estimate, TTC threshold, or actuation frame)
3. **What behavior actually occurred?** (Logged telemetry and actual output measurements)
4. **Did the test pass or fail?** (Deterministic assertion evaluation with tolerance boundaries)
5. **What evidence proves the result?** (Structured failure bundle with logs, input/output JSONs, and stack trace)

---

## 2. Test Suite Taxonomy

| Suite Name | Scope & Purpose | Priority | Typical Execution Time | Example Test Cases |
| :--- | :--- | :---: | :---: | :--- |
| **Smoke** | Sanity validation of ECU boot, queue allocation, and basic packet unpacking | Critical | $< 1$ ms | `TC-SMK-001`, `TC-SMK-002`, `TC-SMK-003` |
| **Functional** | Normal ADAS operations (Kalman filter, Collision warning TTC, Fusion) | High | $< 5$ ms | `TC-FUN-001`, `TC-FUN-002`, `TC-FUN-003`, `TC-FUN-004` |
| **Safety** | Abnormal conditions, watchdog deadline violations, and safe-state transitions | Critical | $< 5$ ms | `TC-SAF-001`, `TC-SAF-002`, `TC-SAF-003`, `TC-SAF-004` |
| **CAN** | Frame layout, DLC enforcement, unknown message rejection, brake broadcasts | High | $< 2$ ms | `TC-CAN-001`, `TC-CAN-002`, `TC-CAN-003`, `TC-CAN-004` |
| **Fault Injection** | Controlled anomalies: sensor blackout, CAN timeout, out-of-range inputs | High | $10 - 60$ ms | `TC-FLT-001`, `TC-FLT-002`, `TC-FLT-003`, `TC-FLT-004` |
| **Regression** | Aggregation of all tagged regression tests across all suites | High | $< 70$ ms | All tests tagged with `regression` (14 tests) |

---

## 3. Determinism & Isolation Rules

1. **Zero Randomness without Seed**: All synthetic sensor trajectories use deterministic time-series equations.
2. **Independent State**: Each test instantiates a clean ECU model and simulated bus fixture, preventing state leakage across tests.
3. **Guaranteed Cleanup**: The test runner executes teardown logic in a `finally` block regardless of assertion pass or fail.
4. **Tolerance-Bounded Assertions**: Floating-point kinematics (Kalman positions and TTC calculations) use calibrated tolerances (e.g. $\pm 0.5$m) to accommodate numerical quantization.

---

## 4. Failure Evidence Collection Policy

Whenever an assertion fails or an unexpected exception occurs during a test:
1. Execution is immediately halted for that test case.
2. The runner flags the test as `FAILED` or `ERROR`.
3. An isolated evidence folder is generated at `reports/runs/<run_id>/evidence/<test_id>/`:
   - `result.json`: Test metadata, duration, expected vs actual values.
   - `execution.log`: Microsecond-timestamped log trace of task execution.
   - `input.json`: Exact stimulus injected during the test.
   - `output.json`: Actual observed output from the ECU.
4. The test ID is appended to the failed tests registry, enabling re-runs via `adas-test run --failed`.

---

## 5. CI/CD Integration Guide

The CLI harness is engineered for continuous integration (GitHub Actions, Jenkins, GitLab CI).

### Example GitHub Actions Workflow (`.github/workflows/test.yml`):
```yaml
name: ADAS ECU Automated Testing
on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install Dependencies
        run: pip install -r requirements.txt
      - name: Run Regression Suite
        run: ./adas-test regression
      - name: Publish JUnit Test Results
        uses: EnricoMi/publish-unit-test-result-action@v2
        if: always()
        with:
          files: reports/runs/*/junit.xml
      - name: Upload HTML Test Report
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: test-report
          path: reports/latest_report.html
```
