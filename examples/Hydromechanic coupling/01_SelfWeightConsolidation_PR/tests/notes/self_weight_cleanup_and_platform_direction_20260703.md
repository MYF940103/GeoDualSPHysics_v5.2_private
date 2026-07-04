# Self-weight tests cleanup and platform-direction note

Date: 2026-07-03

## Cleanup

Removed concluded temporary test outputs, figures, configs, logs, and test BAT files from:

- `tests/outputs`
- `tests/figures`
- `tests/configs`
- `tests` root run logs

The removed groups were already summarized in previous notes:

- `self_weight_scenario2_platform_diag_20260703.md`
- `self_weight_head_neumann_ghost_20260703.md`
- `self_weight_mdbcc0_pore_predictor_only_test_20260703.md`

The retained complete baseline groups are:

- `outputs/CaseSWStage1_TwoStage_Damp002_DrainShep40_t040_GPU_out`
- `outputs/CaseSWScenario2_TwoStage_Damp002_DTv0005_from_p0060_GPU_out`
- `figures/CaseSWStage1_TwoStage_Damp002_DrainShep40_t040_GPU`
- `figures/CaseSWScenario2_TwoStage_Damp002_DTv0005_from_p0060_GPU`
- `configs/CaseSWStage1_TwoStage_Damp002_DrainShep40_t040_Def.xml`
- `configs/CaseSWScenario2_TwoStage_Damp002_DTv0005_Def.xml`

## Current conclusion

The late bottom excess pore-pressure platform is most likely a bottom mDBC boundary-consistency problem in the pore-pressure-rate loop, not a global consolidation-time-scale error.

Evidence so far:

- Early and mid-time profiles agree with Terzaghi theory, so `khyd`, `Tv`, and drainage at the top are not the primary cause.
- Changing `CteB/Cs0`, soil damping, fixed-time-step semantics, and mDBC pore-pressure extrapolation cadence did not remove the late platform.
- Excluding boundary Darcy terms improved a late-window slope but failed in full-history validation, which means deleting boundary seepage is not a clean fix.
- Near the bottom, fluid-neighbor drainage and mDBC boundary-neighbor contributions nearly cancel at late time. The remaining net pore-pressure rate becomes too small, producing the platform.

## Next direction

Do not return to the simple boundary-seepage exclusion state.

Keep mDBC boundary pressure participating in the hydraulic operator, but debug and then modify the boundary-neighbor treatment so it is consistent with an impermeable hydraulic-head Neumann ghost and with the mDBC mechanical ghost velocity used by the compression/divergence term.

Recommended order:

1. Keep the retained source change where `MDBCCorrector=0` applies pore-pressure mDBC extrapolation only with mDBC mechanical extrapolation.
2. Diagnose the bottom-band pore-pressure-rate terms with boundary neighbors included:
   - compression term from `divv`;
   - Darcy/head term from `lapw/lapz`;
   - fluid-neighbor versus boundary-neighbor split.
3. Check whether the mDBC ghost velocity used in the pore-pressure compression term matches the slip mode and the velocity actually used in force/mDBC correction.
4. If the velocity path is not enough, implement a pairwise impermeable hydraulic-head ghost for boundary-neighbor Darcy terms rather than using ordinary boundary pressure or deleting boundary terms.
5. Validate with a late-window restart first, then a full `Tv=2` two-stage run.
