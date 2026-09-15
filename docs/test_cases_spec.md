# ADAS ECU Test Cases Specification

This document details all 19 automated test cases implemented in the ADAS ECU validation framework.

---

## 1. Smoke Suite

### `TC-SMK-001`: ECU Initialization & State Verification
- **Suite**: Smoke
- **Priority**: Critical
- **Requirement**: NFR-3.4 (System state thread-safety and atomic transitions)
- **Precondition**: Clean uninitialized ECU instance.
- **Stimulus**: Boot the ECU process.
- **Expected Outcome**: Pre-boot state is `INIT`; after boot, watchdog advances state to `RUNNING`; sensor queue is allocated and empty.
- **Tags**: `smoke`, `init`, `state`, `regression`

### `TC-SMK-002`: Basic CAN Sensor Frame Decoding
- **Suite**: Smoke
- **Priority**: High
- **Requirement**: FR-1.1, FR-1.2
- **Precondition**: Virtual CAN bus active.
- **Stimulus**: CAN frame with ID 0x100 (`x=25.5`, `y=-3.2`) and 0x200 (`vx=-12.0`, `vy=0.5`).
- **Expected Outcome**: Frame DLC equals 8; unpacked floating-point coordinates match input within $\pm 0.001$.
- **Tags**: `smoke`, `can`, `sensor`, `regression`

### `TC-SMK-003`: Sensor Queue Bounded Capacity
- **Suite**: Smoke
- **Priority**: High
- **Requirement**: NFR-2.3 (Queue overflow shall not cause failure)
- **Precondition**: ECU in RUNNING state.
- **Stimulus**: Enqueue 10 valid sensor frames, followed by an 11th frame.
- **Expected Outcome**: First 10 frames accepted (queue depth 10); 11th frame dropped without crash; dropped frame counter increments to 1.
- **Tags**: `smoke`, `queue`, `reliability`, `regression`

---

## 2. Functional Suite

### `TC-FUN-001`: Kalman Filter State Estimation Convergence
- **Suite**: Functional
- **Priority**: High
- **Requirement**: FR-2.1, FR-2.2
- **Precondition**: Kalman filter initialized at `x=50.0m`, `vx=-10.0m/s`.
- **Stimulus**: 50 cycles of approach with noisy position measurements.
- **Expected Outcome**: Estimated state vector tracks kinematic trajectory within $\pm 0.5$m position and $\pm 0.5$m/s velocity.
- **Tags**: `functional`, `kalman`, `fusion`, `regression`

### `TC-FUN-002`: Collision Detector Warning Threshold Trigger
- **Suite**: Functional
- **Priority**: High
- **Requirement**: FR-3.1
- **Precondition**: Target vehicle approaching along ego path.
- **Stimulus**: $x = 25.0$m, $v_x = -10.0$m/s ($TTC = 2.5$s).
- **Expected Outcome**: `is_approaching` is True; $TTC = 2.5 \pm 0.05$s; `risk_level` is `WARNING`; `should_brake` is False.
- **Tags**: `functional`, `collision`, `ttc`, `regression`

### `TC-FUN-003`: Collision Critical Emergency Brake Actuation
- **Suite**: Functional
- **Priority**: Critical
- **Requirement**: NFR-3.3
- **Precondition**: Imminent collision scenario.
- **Stimulus**: $x = 12.0$m, $v_x = -12.0$m/s ($TTC = 1.0$s).
- **Expected Outcome**: `time_to_collision` $< 1.5$s; `risk_level` is `CRITICAL`; `should_brake` is True.
- **Tags**: `functional`, `safety`, `brake`, `regression`

### `TC-FUN-004`: Multi-Sensor Fusion Data Composition
- **Suite**: Functional
- **Priority**: Medium
- **Requirement**: FR-1.4
- **Precondition**: Multi-sensor scenario generation active.
- **Stimulus**: Synchronized Lidar, Radar, Camera, and Ultrasonic frame generation.
- **Expected Outcome**: Sensor frame contains valid position, camera classification (vehicle/pedestrian), and confidence $> 0.9$.
- **Tags**: `functional`, `sensor`, `fusion`

---

## 3. Safety Suite

### `TC-SAF-001`: Watchdog Compute Deadline Violation Handling
- **Suite**: Safety
- **Priority**: Critical
- **Requirement**: FR-3.3, FR-3.5
- **Precondition**: ECU in RUNNING state with 50ms watchdog deadline.
- **Stimulus**: Inject compute execution delay of $65,000\,\mu\text{s}$ ($65$ms).
- **Expected Outcome**: Watchdog sets `deadline_violated = True`, transitions ECU state to `SAFE`, commands emergency brake, and emits CAN 0x400.
- **Tags**: `safety`, `watchdog`, `deadline`, `regression`

### `TC-SAF-002`: Emergency Brake Actuation & Frame Broadcast
- **Suite**: Safety
- **Priority**: Critical
- **Requirement**: FR-3.4, NFR-3.3
- **Precondition**: ECU running nominally.
- **Stimulus**: Invoke `trigger_emergency_brake()`.
- **Expected Outcome**: State transitions to `SAFE`; brake command CAN frame 0x400 emitted with payload `0xFF`.
- **Tags**: `safety`, `brake`, `can`, `regression`

### `TC-SAF-003`: System State Machine Transition Validation
- **Suite**: Safety
- **Priority**: High
- **Requirement**: NFR-3.4
- **Precondition**: ECU in INIT state.
- **Stimulus**: Sequentially trigger boot, compute overrun, and critical fault.
- **Expected Outcome**: State advances in order: `INIT` $\rightarrow$ `RUNNING` $\rightarrow$ `SAFE` $\rightarrow$ `FAULT`.
- **Tags**: `safety`, `state_machine`, `regression`

### `TC-SAF-004`: Fault State Operation Inhibition
- **Suite**: Safety
- **Priority**: High
- **Requirement**: FR-3.5
- **Precondition**: ECU in FAULT state.
- **Stimulus**: Submit nominal compute cycle.
- **Expected Outcome**: Compute cycle is inhibited; state remains `FAULT`; no dequeuing occurs.
- **Tags**: `safety`, `fault`, `regression`

---

## 4. CAN Suite

### `TC-CAN-001`: Standard CAN Frame Structure & DLC Verification
- **Suite**: CAN
- **Priority**: High
- **Requirement**: FR-1.1, FR-1.2
- **Precondition**: Pack Lidar and Radar messages.
- **Stimulus**: Encode test sensor coordinates.
- **Expected Outcome**: Frame DLC is 8 bytes; payload buffers are exactly 8 bytes long.
- **Tags**: `can`, `format`, `dlc`, `regression`

### `TC-CAN-002`: Unknown CAN Arbitration ID Filtering
- **Suite**: CAN
- **Priority**: Medium
- **Requirement**: NFR-2.4
- **Precondition**: Virtual bus initialized.
- **Stimulus**: Transmit frame with foreign ID 0x7FF.
- **Expected Outcome**: Frame ignored by sensor parser; zero Lidar/Radar frames queued from foreign ID.
- **Tags**: `can`, `filter`, `robustness`

### `TC-CAN-003`: Extended Sensor CAN Frames Parsing
- **Suite**: CAN
- **Priority**: Medium
- **Requirement**: FR-1.4
- **Precondition**: Extended sensor encoder available.
- **Stimulus**: Encode Camera frame (0x250, pedestrian class 2, confidence 0.88) and Ultrasonic frame (0x300, 142.5 cm).
- **Expected Outcome**: Payloads correctly decoded into physical engineering units.
- **Tags**: `can`, `camera`, `ultrasonic`

### `TC-CAN-004`: Emergency Brake Broadcast Frame Layout
- **Suite**: CAN
- **Priority**: Critical
- **Requirement**: NFR-3.3
- **Precondition**: Brake encoder available.
- **Stimulus**: Generate brake actuation CAN frame.
- **Expected Outcome**: ID equals `0x400`, DLC equals 1, data byte equals `0xFF`.
- **Tags**: `can`, `brake`, `safety`, `regression`

---

## 5. Fault Injection Suite

### `TC-FLT-001`: Sensor Dropout & Dead Reckoning Resilience
- **Suite**: Fault Injection
- **Priority**: High
- **Requirement**: NFR-2.1
- **Precondition**: Kalman filter tracking target at 10 m/s.
- **Stimulus**: Omit sensor measurement updates for 15 cycles (300ms blackout).
- **Expected Outcome**: Filter maintains accurate target position via kinematic dead-reckoning within $\pm 0.2$m.
- **Tags**: `fault`, `dropout`, `kalman`, `regression`

### `TC-FLT-002`: CAN Communication Timeout Detection
- **Suite**: Fault Injection
- **Priority**: High
- **Requirement**: FR-3.1
- **Precondition**: Bus in silence.
- **Stimulus**: Await CAN frame with 50ms timeout.
- **Expected Outcome**: Frame receiver returns None upon timeout expiration without hanging.
- **Tags**: `fault`, `can`, `timeout`, `regression`

### `TC-FLT-003`: Out-of-Range Sensor Measurement Filtering
- **Suite**: Fault Injection
- **Priority**: Medium
- **Requirement**: FR-1.1
- **Precondition**: Input validation filter active.
- **Stimulus**: Inject physically impossible negative distance $x = -500.0$m.
- **Expected Outcome**: Input rejected by range sanitization guard.
- **Tags**: `fault`, `sensor`, `range`

### `TC-FLT-004`: Corrupted CAN Payload Handling Resilience
- **Suite**: Fault Injection
- **Priority**: Medium
- **Requirement**: NFR-2.4
- **Precondition**: CAN payload mutation injector.
- **Stimulus**: Invert payload bytes using XOR bitmask 0xFF.
- **Expected Outcome**: Frame decoder processes corrupted bytes with defensive error handling; no process crash.
- **Tags**: `fault`, `can`, `corrupt`, `robustness`
