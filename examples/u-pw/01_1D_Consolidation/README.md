# 01 1D Consolidation

CPU smoke/regression anchor for the u-pw PR prototype.

## Formal Files

- `Case1DConsolidation_PR_Def.xml`
- `xCase1DConsolidation_PR_win64_CPU_debug.bat`
- `Case1DConsolidation_PR_SelfWeight_Scenario2_T3p6_Xi010_Def.xml`
- `xCase1DConsolidation_PR_SelfWeight_Scenario2_T3p6_Xi010_win64_CPU_release.bat`
- `SW3h_scenario2_T3p6_xi010/`

The first pair is the pressure-only 1D diffusion baseline. The SW3h files and
result directory are retained as a documented long-run diagnostic result from
the CPU development phase.

## Smoke Status

Latest short pressure-only smoke:

- temporary copy of `Case1DConsolidation_PR_Def.xml`
- `TimeMax=0.0005`
- `TimeOut=0.0005`
- CPU Debug
- `code=0`
- `excluded=0`
- CSV output contained `PorePress`, `ExcessPorePress`, `PorePressRate`,
  `DivVel`, `LapPorePress`, and `LapZ`

The temporary smoke output was removed after verification.

## Experiments

`experiments/` contains historical diagnostics and smoke-test templates from
the CPU development phase. These are not formal reproduction cases unless their
local README or notes say otherwise.

### ExternalLoad L2 Paper-Aligned

`experiments/ExternalLoad_L2_PaperAligned/` is the current paper-aligned
external-load probe. It uses:

- `H=1.0 m`, `width=0.1 m`, `Dp=0.01 m`;
- `E=2e6 Pa`, `nu=0.3`, `Kw=2e8 Pa`, `n=0.3`, `k=1e-3 m/s`;
- `SoilConstitutiveModel=0`;
- native `AccInput` on the top `mkfluid=1` material layer, mapped to
  `q0=-10 kPa` as `a_z=-476.190476 m/s2`;
- `PorePressureBoundaryOperator=0`;
- top drained and bottom no-flux layer corrections;
- CPU and GPU Release short runs.

Both CPU and GPU short runs finished with `code=0`, `excluded=0`, and
`DtMin=0`, and the top/bottom hydraulic boundary diagnostics were clean.
However, the `q0=-10 kPa` AccInput route generated a much larger dynamic
excess-pressure response than the Terzaghi analytical curve. Treat L2 as a
paper-aligned setup and loading-route diagnostic, not as a strict paper
validation curve.

### ExternalLoad L3 Initial-Pressure Gate

`experiments/ExternalLoad_L3_InitialPressureGate/` is the no-source L3 route
audit result. It keeps the L2 paper constants but removes mechanical
`AccInput` and initializes a uniform `10 kPa` excess pore-pressure field with
`PorePressureInit=3`.

- CPU Release: `code=0`, `excluded=0`, `DtMin=0`.
- GPU Release: `code=0`, `excluded=0`, `DtMin=0`.
- Top drained residual is `0 Pa`; bottom no-flux proxy is about `0.002 Pa`.
- Velocity remains `0 m/s`, confirming that the L2 dynamic peak came from the
  loading route.
- Bottom RMSE versus the `q0=10 kPa` Terzaghi curve improves by about `30x`
  relative to L2; final profile RMSE improves by about `5.25x`.

L3a is an analytical PR diffusion/boundary gate, not a mechanical surface-load
reproduction. Because `PorePressureFeedback=0`, it does not validate the full
coupled Terzaghi storage response. A future strict route should use a loading
plate/surface traction or a stress/pore-pressure consistent initialization.

### ExternalLoad L3b Mechanical Top-Load Prototype

`experiments/ExternalLoad_L3b_MechanicalTopLoad/` tests the first CPU-only
source-backed mechanical surcharge route. It adds `MechanicalTopLoad=1`, removes
`AccInput`, and applies `Fz=q0*A` to the detected top material surface.

- CPU Release: `code=0`, `excluded=0`, `DtMin=0`.
- `q0=-10 kPa` and `A=0.1 m2` produce the intended `|Fz|=1000 N` load scale.
- GPU simulation is deferred because this prototype is CPU-only and hard-errors
  on GPU.
- Top drained and bottom no-flux checks remain reasonable.
- The generated excess-pressure peak is still about `5.9e5 Pa`, so the route is
  not close to the Terzaghi analytical initial-value problem.

L3b is useful because it proves that the load-route blocker is not just the
native `AccInput` file mechanism. Directly forcing top material particles still
behaves dynamically. Do not use L3b as a strict paper validation curve.

### ExternalLoad L3c Consistent Initial State

`experiments/ExternalLoad_L3c_ConsistentInitialState/` formalizes the
paper-compatible Terzaghi initial-value gate:

- `PorePressureInit=3` with uniform `PorePressureExcessAmp=10000 Pa`;
- `InitialStressMode=0`, because the instantaneous undrained analytical
  condition carries the surcharge as pore pressure, not effective stress;
- no `AccInput`;
- no `MechanicalTopLoad`;
- `PorePressureFeedback=0`;
- top drained from initialization and bottom no-flux correction enabled.

Both CPU and GPU Release runs finished with `code=0`, `excluded=0`, and
`DtMin=0`. L3c matches L3a, avoids the L2/L3b dynamic excess-pressure peak,
and keeps the pressure scale at `10 kPa`. It should be treated as the current
PR diffusion/boundary plus initial-state validation gate, not as a full
mechanical load-generation reproduction.

### L3e Validation Package

`experiments/L3e_ValidationPackage/` consolidates L1, L2, L3a, L3b, and L3c.
It adds no new simulation and no source changes.

The package classifies:

- L3a/L3c as the current validation-ready PR diffusion and hydraulic-boundary
  gates;
- L1/L2/L3b as stable reduced smoke or loading-route diagnostics;
- L3d mechanical top-load reproduction as deferred.

Use L3c for the current paper-compatible 1D consolidation validation figure.
Do not use L2/L3b as strict Terzaghi validation curves, and do not start a
damping/viscosity sweep before the mechanical loading route is redesigned.

## Policy

Do not use this directory for broad damping/viscosity sweeps before the loading
route is fixed. Future strict reproduction curves should separate the PR
diffusion gate from the mechanical load-generation route.

## L4-L5 Decision Roadmap

The L4-L5 decision audit defines strict 1D consolidation reproduction in three
levels:

- Level 1: PR diffusion and hydraulic-boundary gate. L3c and the proposed L4
  GPU long-run belong here.
- Level 2: mechanical top-surcharge generation. L2 and L3b are stable attempts
  but do not pass this layer because they over-generate dynamic excess pressure.
- Level 3: fully coupled hydromechanical response with feedback/stress
  coupling. This remains deferred.

Recommended next step: run L4 first as a low-risk GPU long-run of the L3c
initial-state route. L4 can strengthen the paper-compatible diffusion and
boundary figure, but it must not be described as full mechanical reproduction.

L5 remains required for a complete strict reproduction because the top
surcharge `q0` must eventually be generated through a paper-faithful mechanical
route, such as a force-controlled plate, true surface traction, or a consistent
total/effective stress initializer. L5 should be CPU-first and should not block
L4. Full feedback and damping/viscosity sweeps remain deferred.

### ExternalLoad L4 GPU Long-Run

`experiments/ExternalLoad_L4_GPU_LongRun/` extends the L3c initial-state gate to
`TimeMax=0.08 s` on GPU.

- GPU Release: `code=0`, `excluded=0`, `DtMin=0`.
- `Tv_final≈2.23e-2`.
- Peak excess pressure remains at the intended `10 kPa` scale.
- Pressure decays monotonically and remains bounded.
- Final top drained residual is `0 Pa`; final bottom no-flux proxy is about
  `-2.4e-7 Pa`.
- A matching L4 CPU long run was not run because L3c CPU already cost several
  minutes for one quarter of this duration; L3c CPU/GPU parity remains the
  parity reference for this route.

L4 is a Level-1 PR diffusion and boundary validation figure. It is not a
mechanical top-load reproduction, and the longer window shows that the current
feedback-off pressure gate dissipates faster than the Terzaghi
constrained-storage analytical reference. L5 remains the future route for
strict mechanical loading.

### ExternalLoad L5 Feedback-On Gate

`experiments/ExternalLoad_L5_FeedbackOnGate/` turns on pore-pressure momentum
feedback in the L3c initial-state route:

- `PorePressureInit=3`;
- `PorePressureFeedback=1`;
- `PorePressureFeedbackMode=1`;
- `PorePressureFeedbackOperator=1`;
- no `AccInput`;
- no `MechanicalTopLoad`;
- `InitialStressMode=0`.

CPU low-amplitude (`p_w0=1 kPa`), CPU target-amplitude (`p_w0=10 kPa`), and
GPU target-amplitude runs all finished with `code=0`, `excluded=0`, and
`DtMin=0`. The target pressure peak stays at the intended `10 kPa` scale, and
the top drained / bottom no-flux checks remain small.

This is a feedback-on coupling gate, not strict Terzaghi reproduction. Turning
on feedback introduces finite velocity, `DivVel`, `PorePressRate`, negative
excess-pressure excursions, and non-monotonic mean-pressure decay. It is useful
as a minimum coupling check before a CPU-first reduced landslide baseline, but
L3c/L4 remain the clean Level-1 PR diffusion/boundary validation figures.

L5b consistent stress initialization remains the recommended 1D path if a
stricter coupled consolidation validation is needed. Damping and viscosity
sweeps are still not recommended before the loading/initial-state route is
settled.

### BND1 Operator 2 Generalized Boundary Audit

`experiments/BND1_Operator2Generalized/` generalizes the CPU-only
`PorePressureBoundaryOperator=2` prototype so ordinary solid boundary particles
are treated as hydraulic no-flux boundary samples. The patch does not change the
default operator, does not change mode `0` or mode `1`, and does not port mode
`2` to GPU.

Short CPU checks show the generalized operator is active:

- mode `2` reports ordinary solid no-flux boundary contribution pairs;
- feedback-off mode `2` finishes with `code=0`, `excluded=0`, `DtMin=0`;
- feedback-on mode `2` is not stable at the L5 target amplitude
  (`excluded=973`, `DtMin adjustments=10252`).

Decision: mode `2` is a useful CPU boundary-method prototype, but it is not
recommended as default, not ready for GPU, and not ready for a landslide
baseline. Keep mode `1` as the current feedback-on 1D gate while BND2/BND4 are
planned.

### TINT1 Pore-Pressure Time-Integration Audit

`experiments/TINT1_PorePressureTimeIntegration/` is an audit-only package. It
does not add new simulations and does not change source code.

The audit found that the PR pressure rate is computed during the force
interaction stage. The scalar pressure update then runs before the Verlet
mechanical update or before the Symplectic corrector. Feedback acceleration
uses the pressure available during interaction, not the pressure just produced
by the update.

This is a first-order explicit operator split, not a density-like or
stress-like predictor/corrector update. It is acceptable for the existing
L3c/L4 feedback-off diffusion gates, but it is a plausible contributor to the
BND1 mode `2` feedback-on instability. Do not continue promoting boundary mode
`2` before a CPU-only TINT2 time-integration experiment is tested.

### TINT1b Dependency and Update-Stage Plan

TINT1b extends the TINT1 audit to every pressure-related variable:
`PorePress`, `PorePressRate`, `DivVel`, `LapPorePress`, `LapZ`, boundary
operator contributions, feedback acceleration, Shepard, and top/bottom clamps.
It adds no source changes and no new runs.

Main planning result:

- `PorePressRate` is an interaction-stage value.
- `PorePress` is updated explicitly and may then be changed by Shepard or
  top/bottom boundary projections.
- feedback acceleration should be treated as using previous-step/stage
  pressure in the first TINT2 experiment.
- moving only `UpdatePorePressure` is not enough; the TINT2 patch should move
  the pressure update plus Shepard and clamps as a single end-step pressure
  commit.

Recommended TINT2 scope:

- add `PorePressureTimeIntegrationMode=1` as CPU-only end-step update;
- keep mode `0` as default;
- avoid adding a permanent diagnostics parameter unless absolutely necessary;
- use postprocessing for `DeltaP_rate` versus `DeltaP_actual` bookkeeping;
- keep GPU nonzero modes deferred.

### TINT2 End-Step Pore-Pressure Commit

`experiments/TINT2_PorePressureEndStepUpdate/` implements and tests
`PorePressureTimeIntegrationMode=1` as a CPU-only end-step pressure commit:

```text
Interaction_Forces -> ComputeVerlet/ComputeSymplecticCorr -> pressure commit
```

The pressure commit block contains the raw pressure update, Shepard correction,
top drained clamp, bottom no-flux projection, and existing hydraulic clamp
logic where applicable. Mode `0` remains the default and keeps the old ordering.
GPU nonzero modes hard-error.

Short CPU results:

- L3c feedback-off operator `1`: mode `1` is stable and numerically unchanged
  from mode `0`;
- L5 feedback-on operator `1`: mode `1` is stable and numerically unchanged;
- BND1 generalized operator `2` feedback-off: unchanged;
- BND1 generalized operator `2` feedback-on: still unstable
  (`excluded=973`, `DtMin=10252`).

Decision: mode `1` clarified the staging semantics but did not improve the
BND1 mode `2` instability. Keep it as active experimental CPU-only until
TINT2-clean decides whether to deprecate/delete it. Do not port it to GPU and
do not continue adding more time-integration modes before cleanup.
