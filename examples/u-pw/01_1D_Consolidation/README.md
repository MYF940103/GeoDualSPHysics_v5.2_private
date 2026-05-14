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

## Policy

Do not use this directory for further CPU long-time parameter tuning during the
pre-GPU readiness pass. Future strict reproduction curves and sensitivity
studies should move to the GPU workflow after G1-G4 are in place.
