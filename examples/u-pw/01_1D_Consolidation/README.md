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
