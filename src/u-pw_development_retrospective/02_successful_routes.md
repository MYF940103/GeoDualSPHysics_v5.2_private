# Successful Routes Worth Preserving

## 1D PR Diffusion / Boundary Gate

Best current validation route:

```text
PorePressureInit=3
p_w0=10 kPa
InitialStressMode=0
PorePressureFeedback=0
PorePressureBoundaryOperator=1 or existing validated route
no AccInput
no MechanicalTopLoad
```

Why keep it:

- CPU/GPU code=0, excluded=0, DtMin=0 in L3c/L4;
- peak excess remains at the intended 10 kPa scale;
- top drained and bottom no-flux checks are clean;
- useful paper-compatible Level-1 diffusion/boundary figure.

Keep/cherry-pick candidates:

- `PorePressureInit=3`;
- scripts and analytical reconstruction from L3c/L4/L3e;
- docs defining Level-1 vs mechanical reproduction.

## L5 Feedback-On 1D Coupling Gate

Best current feedback-on pre-landslide gate:

```text
PorePressureFeedback=1
PorePressureFeedbackMode=1
PorePressureFeedbackOperator=1
PorePressureInit=3
PorePressureBoundaryOperator=1
no AccInput
no MechanicalTopLoad
```

Why keep it:

- CPU and GPU target-amplitude cases finished with code=0, excluded=0,
  DtMin=0;
- pressure peak stayed near the physical initial 10 kPa scale;
- useful as a coupling stability gate before any slope/landslide work.

Caveat: not strict Terzaghi mechanical loading reproduction.

## DP Feedback-Off Triaxial Platen Route

Useful as a reduced diagnostic workflow:

- explicit top/bottom platen workflow;
- feedback off;
- pairwise reaction diagnostics;
- T5/T5b/T5c DP comparison package.

Keep the final reports, CSV summaries, and plotting scripts. Archive raw runs
and intermediate geometry variants.

## MCC Material-Point And CPU Prototype

Keep:

- M2 Python reference logic;
- M3a C++ single-point parity helper;
- MCC parser/state/output knowledge;
- caveated CPU stress-update prototype reports.

Do not carry forward as clean validation until boundary/layout issues are
resolved.

## Interface Registry And Cleanup Policy

Keep permanently:

- `experimental_interface_registry.md`;
- `experimental_interface_cleanup_policy.md`;
- `tint2_interface_constraint.md`.

These documents are a process success and should be copied into any rebuilt
branch before new u-pw parameters are added.
