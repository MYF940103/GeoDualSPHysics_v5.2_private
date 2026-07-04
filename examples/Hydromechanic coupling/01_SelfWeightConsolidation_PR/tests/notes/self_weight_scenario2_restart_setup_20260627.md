# Self-weight Scenario 2 restart setup, 2026-06-27

Scenario 2 is now prepared as a true restart calculation from the selected Stage 1 handoff state.

## Restart source

- Formal Stage 1 case: `CaseSelfWeightConsolidation_Stage1`
- Formal Stage 1 duration: `0.30 s`
- Stage 1 output interval: `0.005 s`
- Scenario 2 default restart part: `Part_0060`
- Required restart files:
  - `CaseSelfWeightConsolidation_Stage1_out/data/Part_0060.bi4`
  - `CaseSelfWeightConsolidation_Stage1_out/data/PartExtra_0060.bi4`

The `PartExtra` file is required because the case uses mDBC and Stage 1 must preserve the extra boundary-particle state for restart.

## Scenario 2 inheritance settings

- `HydroMechInitMode=0`
- `HydroMechDrainage=1`
- `HydroMechDrainageStartTime=0`
- Run command uses `-partbegin:60:0 "CaseSelfWeightConsolidation_Stage1_out\data"`

With `HydroMechInitMode=0`, the restart path inherits `PorePress`, `PorePress0`, and `Sigma` from the Stage 1 bi4 files instead of recomputing the initial state from the analytical 1D formula. This avoids the small initial overshoot seen when Scenario 2 starts from `HydroMechInitMode=3`.

## Output interval

Scenario 2 output is set to a uniform nondimensional interval:

- `Delta Tv=0.005`
- `cv=kM/(rho_w g)=0.274445228574 m^2/s`
- `H=1 m`
- `TimeOut=DeltaTv*H^2/cv=0.0182185714 s`

The post-processing script uses the same `SCENARIO2_TOUT=0.0182185714`, so target-profile matching and summary CSV files remain aligned with the output cadence.

## Running

Use the root workflow bat to run the complete formal sequence:

```bat
xCaseSelfWeightConsolidation_win64_CPU.bat
```

This runs Stage 1 first, then runs Scenario 2 from `Part_0060`.

To run Scenario 2 only after Stage 1 output already exists:

```bat
xCaseSelfWeightConsolidation_Scenario2_win64_CPU.bat 60
```

The Scenario 2 bat checks for both restart files before running.
