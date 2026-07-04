# Self-weight Mode3 standalone pore-rate isolation conclusion

Date: 2026-07-01

## What was tested

Temporarily restored the CPU pore-pressure-rate scheduling to the old standalone path:

- `StInterparmsc` received `NULL` for `porepressrate`, so the merged pair-loop pore-rate accumulation was disabled.
- `InteractionPorePressureRate()` was called after `Interaction_Forces_ct()`.
- The current mDBC pore-pressure correction path was kept unchanged.

The temporary source changes were reverted after the run and CPU Debug/Release were rebuilt successfully.

## Result

Case: `CaseSWScenario2_Mode3_StandaloneRate_CPU`

- Solver completed successfully with `Excluded particles=0`.
- `HydroMechInitMode=AnalyticalSelfWeight1D`.
- `sigma_zz min=-43.1867`, confirming the buoyant self-weight initialization branch was active.
- Early and middle dissipation improved and followed theory well:
  - Tv=0.25: SPH bottom EPWP 4.786 kPa, theory 4.705 kPa.
  - Tv=0.50: SPH bottom EPWP 2.600 kPa, theory 2.537 kPa.
- Late dissipation still remained above the old CPU baseline and theory:
  - Tv=1.0: SPH bottom EPWP 1.035 kPa, theory 0.739 kPa.
- Old CPU comparison status: `DIFFERENT`.
  - Bottom max abs difference from old CPU: 0.337568 kPa.
  - Bottom RMS difference from old CPU: 0.0942985 kPa.
  - Target-point max abs bottom difference: 0.240093 kPa.
  - Target-point max abs RMS-profile difference: 148.401 Pa.

## Decision

The merged pore-pressure-rate path is not the sole reason the current Mode3 result does not reproduce the old CPU baseline. Restoring the old standalone pore-rate scheduling improves early/mid behavior but does not recover the full old CPU curve.

Do not start the two-stage Mode3 workflow yet. Continue checking remaining code/configuration differences that can affect the late-time consolidation path.

## Files kept

- `tests/outputs/CaseSWScenario2_Mode3_StandaloneRate_CPU_out`
- `tests/figures/CaseSWScenario2_Mode3_StandaloneRate_CPU`
- `tests/figures/CaseSWScenario2_Mode3_StandaloneRate_CPU_vs_old_cpu`
- `tests/notes/self_weight_mode3_standalone_porerate_cpu_vs_old_cpu_20260701.md`
