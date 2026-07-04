# Self-weight Scenario 2 free-slip mDBC corrector test, 2026-06-28

Purpose:
- Re-run the full Scenario 2 consolidation restart from the retained Stage 1 baseline at `Part_0060`.
- Keep the lateral periodic boundary active, so only the bottom mDBC boundary behavior is changed.
- Compare the previous `SlipMode=1` baseline against `free-slip + MDBCCorrector=0`.

Input files:
- XML: `tests/configs/CaseSWScenario2_restart_p0060_D_DTv0005_freeslip_mdbcc0_Def.xml`
- BAT: `tests/xCaseSWScenario2_restart_p0060_D_DTv0005_freeslip_mdbcc0_win64_GPU.bat`
- Restart source: `tests/outputs/CaseSWStage1_d02_D_SH40_FS_out/data/Part_0060.bi4`
- Restart extra source: `tests/outputs/CaseSWStage1_d02_D_SH40_FS_out/data/PartExtra_0060.bi4`

Key settings:
- `SlipMode=3`, executed with `-mdbc_freeslip`.
- `MDBCCorrector=0`, confirmed at runtime as `mDBC-Corrector=False`.
- `HydroMechDrainage=1`.
- `PoreShepardRegularization=0`.
- `DtFixed=1e-6 s`.
- `TimeMax=3.85 s`.
- `TimeOut=0.0182185714 s`, equivalent to `Delta Tv=0.005`.
- `XPeriodicIncZ=0`, confirmed at runtime as `PeriodicActive="Axis-X"`.

Runtime confirmation:
- `SlipMode="Free slip"`.
- `mDBC-Corrector=False`.
- `PartBegin=60`.
- `Restart hydromechanical data: PorePress and PorePress0 inherited.`
- `Restart soil data: Sigma inherited, Kplastic reset for restart stage.`

Output paths:
- Full output: `tests/outputs/CaseSWScenario2_restart_p0060_D_DTv0005_freeslip_mdbcc0_out`
- Per-case figures: `tests/figures/CaseSWScenario2_restart_p0060_D_DTv0005_freeslip_mdbcc0`
- Boundary-mode comparison figures: `tests/figures/CaseSWScenario2_restart_p0060_D_DTv0005_freeslip_mdbcc0_compare`

Post-processing:
- The case BAT runs `tests/support/postprocess_scenario2_restart.py` after the solver finishes.
- A watcher should run `tests/support/compare_scenario2_boundary_modes.py` after the case BAT exits to compare against the previous `SlipMode=1` baseline.

Post-run observations:
- The full run finished with code 0 and excluded particles = 0.
- The `free-slip + MDBCCorrector=0` result is almost identical to the previous `SlipMode=1` baseline.
- At `Tv=1`, bottom excess pore pressure is about `1.0816 kPa`, while the Terzaghi reference is about `0.7388 kPa`; the late-time dissipation remains too slow.
- The bottom-pressure comparison and profile RMS show only tiny changes relative to the previous run, so the velocity slip mode is not the dominant error source for this 1D periodic-sidewall setup.

Important implementation detail:
- In the current CPU and GPU loops, `MDBCCorrector=0` does not fully suppress corrector-step pore-pressure mDBC correction.
- In the corrector step, the code skips `MdbcBoundCorrection()` but still calls `InteractionPorePressureMdbcCorrection()` when hydromechanics is enabled.
- Therefore this test disabled mechanical mDBC corrector behavior, but boundary pore pressure was still refreshed in the corrector step.

Likely error direction:
- The late-time positive excess-pressure bias is systematic through the lower and middle profile, not only in the first bottom particle layer.
- A bottom-curve time-scale fit gives an effective `cv` around `0.95` of the analytical value over much of the run, falling to about `0.85` by `Tv=1`.
- This points to a combined error from the discrete pore-pressure diffusion operator, bottom mDBC pore-pressure extrapolation, and residual Stage 1 initial-profile mismatch.

Recommended next checks:
- Add a separate switch or change the `MDBCCorrector=0` semantics so corrector-step `InteractionPorePressureMdbcCorrection()` can actually be disabled for pore pressure, then run a short/medium comparison.
- Run a no-mDBC bottom boundary diagnostic if feasible, for example a periodic vertical manufactured diffusion column or a minimal 1D fixed ghost-pore-pressure benchmark, to isolate the diffusion operator from mDBC extrapolation.
- Run a controlled hydraulic-conductivity sensitivity, for example `k=1.03e-3` and `k=1.05e-3`, only as a calibration diagnostic; do not treat it as the physical fix unless the operator/boundary error is accepted.
- Revisit the Stage 1 restart profile and consider starting Scenario 2 from a numerically relaxed analytical state if the initial bottom excess-pressure deficit remains significant.
