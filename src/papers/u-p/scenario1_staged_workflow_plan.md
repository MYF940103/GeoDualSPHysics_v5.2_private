# Scenario 1 Staged Workflow Plan

Date: 2026-05-12

## Objective

Supporting Materials Scenario 1 represents a staged self-weight consolidation
workflow:

1. generate undrained self-weight excess pore pressure while body gravity is on;
2. switch the mechanical body gravity off while hydraulic gravity remains on;
3. activate the drained top boundary and observe excess pore-pressure
   dissipation toward the hydrostatic reference.

The goal of the next phase is a short-to-long GPU production workflow for this
staged response, using the already validated Scenario 2 PR path where possible.

## Why Scenario 1 Starts After Scenario 2 Freeze

Scenario 2 now has:

- GPU long-run stability to `3.6 s`;
- a paper-ready `xi=0.05` line;
- a nominal and calibrated analytical reference;
- boundary/operator audit showing no need to promote mode 1 or mode 2.

This freezes the self-weight Scenario 2 baseline and lets Scenario 1 focus on
staging mechanics rather than boundary/operator redesign.

## Candidate Routes

### Route A: PorePress Restart Workflow

Stage A runs with body gravity on and saves pore pressure, stress, density, and
velocity. Stage B restarts from Stage A with body gravity off and hydraulic
gravity on.

Pros:

- Closest to a true staged simulation.
- Reuses CPU `PorePress` restart work.
- Can inspect continuity at the stage boundary.

Cons:

- GPU restart parity for all hydromechanical fields is higher risk.
- Requires careful mapping of `PorePress`, stress, density, velocity, and
  plastic state.
- Introduces possible state-mapping error into the first GPU Scenario 1 test.

### Route B: BodyGravityStopTime Single-Run Workflow

One run starts with body gravity on. At `BodyGravityStopTime`, mechanical body
gravity becomes zero while `HydraulicGravity` remains active. Top drained can be
activated at the same time or a specified start time.

Pros:

- Smallest moving part for first GPU production workflow.
- Avoids restart field-mapping risk.
- Matches the CPU `BodyGravityStopTime` feature already implemented for this
  purpose.
- Easier to compare CPU/GPU short/medium/long windows.

Cons:

- Less explicit than a two-stage restart workflow.
- Needs careful logging around the gravity switch.
- Still requires checking that stress/velocity response across the switch is
  physical and not impulsive.

## Recommended First Route

Use Route B, the `BodyGravityStopTime` single-run route, as the first GPU
production workflow.

The restart route remains valuable for a follow-up validation phase, but it
should not be the first Scenario 1 GPU path because it mixes staged physics with
restart-state parity.

## Minimal Test Sequence

### S1-0: XML Audit

- Start from the formal Scenario 1 Stage A/B XMLs and the Scenario 2 GPU path.
- Create a single-run `BodyGravityStopTime` XML.
- Confirm:
  - `Gravity=(0,0,-9.81)`;
  - `HydraulicGravity=(0,0,-9.81)`;
  - `BodyGravityStopTime=0.002`;
  - `PorePressureTopDrained=1`;
  - `PorePressureTopDrainedStartTime=0.002`;
  - `PorePressureBottomNoFlux=1`;
  - feedback operator `1`;
  - Shepard and hydromechanical damping enabled as in Scenario 2.

### S1-1: CPU/GPU Short Smoke

- Time window: about `0.003` to `0.005 s`.
- Run CPU Release and GPU Release.
- Compare immediate gravity-switch response.

### S1-2: GPU Medium Run

- Time window: about `0.05` to `0.2 s`.
- Confirm stability, no excluded particles, and dissipative excess trend.

### S1-3: GPU Long Run

- Time window: Scenario-appropriate long run only after S1-1/S1-2 pass.
- Do not combine with restart route unless explicitly scoped.

### S1-4: Analytical / Supporting Comparison

- Reconstruct the Supporting Materials reference for Scenario 1.
- Compare bottom pressure, excess envelope, and profile evolution.
- Clearly distinguish nominal analytical reference from any calibrated effective
  time-factor sensitivity if needed.

## Required Metrics

Each Scenario 1 phase should report:

- `code` and excluded particles;
- no NaN/Inf;
- velocity max/mean and switch-time impulse check;
- settlement / mean z displacement;
- `PorePress` and `ExcessPorePress` profiles;
- bottom pressure and bottom excess pressure;
- top drained excess maxAbs;
- bottom no-flux proxy;
- `PorePressRate`, `DivVel`, `LapPorePress`, `LapZ`;
- `PorePressureAccelDiff` magnitude;
- GPU/CPU field differences for short parity.

## Stop Criteria

Stop and document rather than extending the run if:

- excluded particles exceed zero in short/medium tests;
- pressure oscillation grows rather than dissipates;
- top drained excess is not clamped near zero after activation;
- bottom no-flux proxy grows unexpectedly;
- velocity or settlement shows an obvious switch-time impulse;
- restart route, if tested later, shows mismatch in `PorePress`, stress,
  density, or velocity at the first restarted output.

## Next Concrete Task

The next Codex task should be S1-0/S1-1:

Create a GPU Scenario 1 `BodyGravityStopTime` single-run short-smoke experiment,
run CPU/GPU Release to `0.003-0.005 s`, compare switch-time pore-pressure and
velocity response, clean heavy outputs, and write `gpu_s1_bodygravity_stop_short_report.md`.

## S1-4 Completion Status

S1-1b, S1-2, S1-3, and S1-4 are complete for the
`BodyGravityStopTime` single-run route:

- S1-1b short CPU/GPU parity passed after the GPU body-gravity stop patch.
- S1-2 GPU medium windows to `0.05 s` and `0.2 s` passed.
- S1-3 GPU long run to `3.6 s` passed with `code=0`, `excluded=0`.
- S1-4 generated paper-figure metrics and the technical note
  `paper_scenario1_bodygravity_stop_note.md`.

The restart route remains deferred. The validated production path for the
current paper workflow is the single-run `BodyGravityStopTime` route with
`PorePressureBoundaryOperator=0`.
