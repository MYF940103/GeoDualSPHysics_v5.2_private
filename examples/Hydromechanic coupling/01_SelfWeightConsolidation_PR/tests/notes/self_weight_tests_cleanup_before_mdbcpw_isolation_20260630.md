# SelfWeight consolidation tests cleanup before mDBC pore-pressure scheduling isolation

Date: 2026-06-30

Purpose: clean previous temporary SelfWeight consolidation test outputs before the next minimal isolation run. The next run only changes the pore-pressure mDBC scheduling path: pore-pressure boundary extrapolation is restored to `ApplyPorePressureBoundaries()`, while `MdbcBoundCorrection()` no longer receives `PorePress0/PorePress`. The merged pore-pressure-rate pair loop is left unchanged.

Recorded conclusions from removed test outputs:

- Direct `HydroMechInitMode=AnalyticalSelfWeight1D` GPU replay after the buoyant self-weight fix recovered the expected initial `sigma_zz` level, but the late-time pore-pressure dissipation still did not match the old CPU baseline.
- Replaying old generated XML/input variants did not by itself recover the old CPU baseline, so the remaining difference is more likely tied to current runtime code paths than to only XML generation.
- Tests with larger explicit `speedsound/CteB` did not materially recover the dissipation curve; `CteB` is therefore not treated as the main cause.
- Damping coefficient changes, artificial viscosity toggles, and no-corrected-gradient pore-rate trials did not remove the late-time mismatch robustly.
- The strongest remaining suspect for this isolation step is scheduling/order change in mDBC pore-pressure extrapolation versus the old baseline path.

Cleanup scope:

- Remove previous temporary test output folders under `tests/outputs`.
- Remove previous temporary comparison figures under `tests/figures`.
- Remove previous temporary XML configs under `tests/configs`.
- Remove previous root-level temporary test logs, pid files, and old test bat launchers in `tests`.
- Keep `tests/notes` and `tests/support`.
