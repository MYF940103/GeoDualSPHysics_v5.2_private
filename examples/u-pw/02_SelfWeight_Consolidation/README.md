# 02 Self-Weight Consolidation

Formal CPU smoke-test scaffold for the Supporting Information self-weight consolidation verification of the u-pw PR formulation.

## Scope

- PR formulation only.
- CPU smoke tests only at this stage.
- No long CPU parameter sweeps or full reproduction curves before the GPU port.
- Scenario 1 uses a two-stage restart workflow with restored pore pressure state.
- Scenario 2 uses continuous body gravity with delayed top drainage.

## Formal smoke files

Scenario 1, Stage A:

- `CaseSelfWeightConsolidation_PR_Scenario1_StageA_Def.xml`
- `xCaseSelfWeightConsolidation_PR_Scenario1_StageA_win64_CPU_release.bat`

Stage A keeps body gravity on, initializes hydrostatic pore pressure, keeps top drainage inactive, and generates self-weight excess pore pressure over a short undrained window.

Scenario 1, Stage B:

- `CaseSelfWeightConsolidation_PR_Scenario1_StageB_Def.xml`
- `xCaseSelfWeightConsolidation_PR_Scenario1_StageB_win64_CPU_release.bat`

Stage B restarts from the Stage A final PART file, sets body Gravity to `(0,0,0)`, keeps `HydraulicGravity=(0,0,-9.81)`, activates top drainage, and checks that the restored pore pressure starts dissipating without a restart impulse.

Scenario 2:

- `CaseSelfWeightConsolidation_PR_Scenario2_Def.xml`
- `xCaseSelfWeightConsolidation_PR_Scenario2_win64_CPU_release.bat`

Scenario 2 keeps body gravity on, activates top drainage after the undrained stage, and checks that total pore pressure trends toward the hydrostatic profile.

Legacy placeholder:

- `CaseSelfWeightConsolidation_PR_Scenario1_TODO_Def.xml`
- `xCaseSelfWeightConsolidation_PR_Scenario1_TODO_win64_CPU_debug.bat`

These are historical scaffolds kept for traceability. Use the Stage A/B files for Scenario 1 smoke tests.

## Smoke criteria

Each smoke run should verify:

- solver finishes with `code=0`;
- excluded particles remain `0`;
- no NaN or obvious velocity impulse appears;
- `PorePress`, `ExcessPorePress`, `PorePressRate`, `DivVel`, `LapPorePress`, `LapZ`, and `PorePressureAccelDiff` are written when `SavePorePressure=1`;
- Scenario 1 Stage B log reports `PorePress` restored from restart and XML `PorePressureInit` skipped;
- top drained layer excess pressure is zero after activation;
- bottom no-flux gradient proxy remains small;
- Scenario 2 total `PorePress` trends toward hydrostatic in short smoke windows.

## Latest Smoke Status

CPU Release smoke was run for the formal Scenario 1 Stage A/B route and a short
Scenario 2 copy. Generated outputs were removed after collecting the status.

| Case | Window | Result | Key check |
| --- | --- | --- | --- |
| Scenario 1 Stage A | `TimeMax=0.002` | `code=0`, `excluded=0` | positive self-weight excess generated, max about `1.28e4 Pa` |
| Scenario 1 Stage B | restart from Stage A to `TimeMax=0.01` | `code=0`, `excluded=0` | log reported `PorePress` restored for `1040/1040` particles and XML initialization skipped |
| Scenario 2 | short copy to `TimeMax=0.002` | `code=0`, `excluded=0` | top-drained/no-flux settings parsed and short run remained stable |

Stage B showed dissipative behavior over the short smoke window: `ExcessPorePress`
max decreased from about `1.28e4 Pa` at restart to about `8.17e3 Pa` by the last
output frame. This is a smoke-readiness check only, not a long-time parameter
calibration.

## Notes

The stable long-run diagnostic from the earlier 1D consolidation directory remains in `../01_1D_Consolidation/SW3h_scenario2_T3p6_xi010/`. This directory is now for formal smoke scaffolds, not for CPU long-run tuning.
