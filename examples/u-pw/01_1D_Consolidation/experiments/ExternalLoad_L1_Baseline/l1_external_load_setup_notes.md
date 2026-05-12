# L1 external-load 1D consolidation baseline setup

## Route

This baseline uses the native DualSPHysics `AccInput` route:

- The material column is split into `mkfluid=0` bulk soil and `mkfluid=1` top external-load layer.
- `<execution><special><accinputs>` applies the time-dependent acceleration only to `mkfluid=1`.
- The acceleration history is stored in `ExternalLoadAcc_L1.csv`.

No source-side `TopLoad*` parameters are used or reintroduced.

## Current baseline scope

This is a single baseline external-load smoke case, not a full paper reproduction of all artificial-viscosity or kinematic-damping combinations.

Production hydraulic settings:

- `PorePressureBoundaryOperator=0`
- top drained boundary, activated after the load ramp at `t=0.05 s`
- bottom no-flux layer correction
- `PorePressureFeedback=1`
- `PorePressureFeedbackMode=1`
- `PorePressureFeedbackOperator=1`
- `PorePressureShepard=1`
- `HydromechDamping=1`, `HydromechDampingXi=0.05`

## External-load convention

The baseline acceleration is small and downward. It is intended to demonstrate that XML-native loading can induce a stable pore-pressure and settlement response without relying on deprecated source-side top-load code.

## Limitations

- The top layer is a material loading layer, not a physical loading plate.
- The acceleration magnitude is a baseline smoke value, not a calibrated surcharge reproduction.
- No artificial-viscosity or damping parameter sensitivity is performed in L1.
