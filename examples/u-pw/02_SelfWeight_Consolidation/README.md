# 02 Self-Weight Consolidation

Formal scaffold for the Supporting Information self-weight consolidation verification of the u-pw PR formulation.

## Scope

- PR formulation only.
- CPU-first reproduction.
- Uses body gravity and hydraulic gravity together for Scenario 2.
- Scenario 1 is not fully runnable yet because it needs `PorePress` restart or an explicit body-gravity switch after the undrained stage.

## Files

- `CaseSelfWeightConsolidation_PR_Scenario2_Def.xml`: runnable draft based on the stable SW3h line from `01_1D_Consolidation`.
- `xCaseSelfWeightConsolidation_PR_Scenario2_win64_CPU_release.bat`: CPU Release run/postprocess draft.
- `CaseSelfWeightConsolidation_PR_Scenario1_TODO_Def.xml`: TODO scaffold only.
- `xCaseSelfWeightConsolidation_PR_Scenario1_TODO_win64_CPU_debug.bat`: placeholder that should not be used for production.

## Current status

Scenario 2 has a stable reference line in `01_1D_Consolidation/SW3h_scenario2_T3p6_xi010/`. Scenario 1 requires missing staged restart/state support before strict reproduction.
