# Self-weight Scenario 2 tests cleanup, 2026-06-29

## Cleanup policy

Old run products under `tests/outputs` and `tests/figures` were cleaned after their conclusions had been recorded in notes. Configuration files, BAT files, support scripts, and notes were kept.

The following outputs were kept because they remain useful as restart or baseline evidence:

- `tests/outputs/CaseSWStage1_d02_D_SH40_FS_out`
- `tests/outputs/CaseSWScenario2_restart_p0060_D_DTv0005_out`
- `tests/figures/CaseSWStage1_d02_D_SH40_FS`
- `tests/figures/CaseSWScenario2_restart_p0060_D_DTv0005`

## Recorded conclusions before cleanup

- `SoilDampingCoef=0.02` full Scenario 2 did not remove the late bottom-pressure plateau.
- Applying `SoilDampingCoef=0.02` only in the late window `Tv ~= 0.9 -> 1.0` also did not recover the theoretical dissipation.
- Free-slip mDBC with `mdbccorrector=0` produced nearly the same late dissipation as the earlier slip setting.
- Pure diffusion / diffusion diagnostic tests showed that the pressure-diffusion term itself is active; the late discrepancy should not be described as a simple missing-diffusion problem.
- The interval-averaged component diagnostic showed large cancellation between compression, Darcy pressure diffusion, and gravity-head terms near the bottom.
- Based on the profile evolution, the current working interpretation is that mid/late numerical oscillations during Scenario 2 are likely driving the accumulated deviation. This is more plausible than attributing the whole late error to the initial Stage 1 inherited state, because early profiles agree well with theory and the deviation evolves non-monotonically.

## Next diagnostic target

Find the trigger and timing of the mid/late oscillations by comparing pressure, `divv`, velocity, and stress histories around the intervals where the bottom-pressure curve departs from, partially returns to, and then departs again from the analytical solution.

## Removed run-product directories

Removed from `tests/outputs`:

- `CaseSWScenario2_restart_p0060_D_DTv0005_damp002_out`
- `CaseSWScenario2_restart_p0060_D_DTv0005_freeslip_mdbcc0_out`
- `CaseSWScenario2_restart_p0180_D_DTv0005_damp002_short_out`
- `CaseSWScenario2_restart_p0180_D_DTv0005_damp002_toTv1_out`
- `CaseSWScenario2_restart_p0180_D_rateavg_toTv1_out`
- `CaseSWScenario2_restart_p0180_D_ratediag_1step_out`
- `CaseSWScenario2_restart_p0180_D_ratediag_DTv0005_out`

Removed from `tests/figures`:

- `CaseSWScenario2_restart_p0060_D_DTv0005_damp002`
- `CaseSWScenario2_restart_p0060_D_DTv0005_diffusion_diagnostic`
- `CaseSWScenario2_restart_p0060_D_DTv0005_freeslip_mdbcc0`
- `CaseSWScenario2_restart_p0060_D_DTv0005_freeslip_mdbcc0_compare`
- `CaseSWScenario2_restart_p0060_D_DTv0005_freeslip_mdbcc0_diffusion_diagnostic`
- `CaseSWScenario2_restart_p0060_D_DTv0005_freeslip_mdbcc0_pure_diffusion`
- `CaseSWScenario2_restart_p0060_D_DTv0005_pure_diffusion`
- `CaseSWScenario2_restart_p0180_D_DTv0005_damp002_short`
- `CaseSWScenario2_restart_p0180_D_DTv0005_damp002_toTv1`
- `CaseSWScenario2_restart_p0180_D_rateavg_toTv1`
- `CaseSWScenario2_restart_p0180_D_ratediag_1step`
- `CaseSWScenario2_restart_p0180_D_ratediag_DTv0005`
- `CaseSWScenario2_restart_p0180_D_ratediag_DTv0005_check`
- `scenario2_damping_compare`
