# Self-weight Scenario 2 diffusion-speed diagnostic, 2026-06-28

Purpose:
- Quantify whether the late-time positive excess-pore-pressure bias can be explained as an effective diffusion-speed lag.
- Use already completed Scenario 2 outputs only; no solver source code was changed.

Inputs:
- Baseline: `tests/figures/CaseSWScenario2_restart_p0060_D_DTv0005`
- Free-slip/mDBCCorrector=0: `tests/figures/CaseSWScenario2_restart_p0060_D_DTv0005_freeslip_mdbcc0`

Diagnostic script:
- `tests/support/diagnose_scenario2_diffusion_speed.py`

Generated outputs:
- `tests/figures/CaseSWScenario2_restart_p0060_D_DTv0005_diffusion_diagnostic`
- `tests/figures/CaseSWScenario2_restart_p0060_D_DTv0005_freeslip_mdbcc0_diffusion_diagnostic`

Main result:
- The baseline and free-slip/mDBCCorrector=0 diagnostics are essentially identical.
- Therefore the late-time bias is not controlled by the velocity slip mode, and not explained by the tested mDBC corrector flag.

Bottom-curve cv fits:
- Baseline, `Tv=0.02..1.0`: best `cv/cv_ref = 0.952`, RMS `0.0641 kPa`.
- Baseline, `Tv=0.05..0.5`: best `cv/cv_ref = 0.963`, RMS `0.0206 kPa`.
- Baseline, `Tv=0.5..1.0`: best `cv/cv_ref = 0.940`, RMS `0.0755 kPa`.
- Free-slip/mDBCCorrector=0, `Tv=0.02..1.0`: best `cv/cv_ref = 0.952`, RMS `0.0640 kPa`.
- Free-slip/mDBCCorrector=0, `Tv=0.05..0.5`: best `cv/cv_ref = 0.963`, RMS `0.0207 kPa`.
- Free-slip/mDBCCorrector=0, `Tv=0.5..1.0`: best `cv/cv_ref = 0.941`, RMS `0.0756 kPa`.

Profile cv fits:
- For both runs, the profile fit gives `cv/cv_ref` around `0.923` at `Tv=0.05`, `0.95` at `Tv=0.1`, `0.96..0.97` at `Tv=0.25..0.5`, about `0.94` at `Tv=0.7`, and `0.855` at `Tv=1.0`.
- The `Tv=1.0` profile can be fit very well by the analytical profile with `cv/cv_ref = 0.855`, which is strong evidence for a time-scale lag rather than a purely local bottom-boundary artifact.

Initial condition:
- The initial `Tv=0` profile has RMS excess-pressure mismatch about `0.0986 kPa`.
- Initial bottom excess pressure is lower than the analytical value, but later results become positive-biased, so initial amplitude mismatch alone cannot explain the late-time slow dissipation.

Interpretation:
- Current Scenario 2 behaves like the analytical Terzaghi solution with a slightly reduced effective diffusion coefficient through most of the run, and a stronger apparent lag at late time.
- Candidate causes are the discrete pore-pressure diffusion operator, the way boundary particles participate in the pore-pressure Laplacian, and residual coupled-mechanics effects from the inherited Stage 1 state.

Recommended next step:
- Build a dedicated pure pore-pressure diffusion diagnostic that isolates the SPH Laplacian from deformation, stress evolution, and dynamic momentum feedback.
- Avoid reintroducing a permanent `PoreDiffusionOnly` product switch; keep any diffusion-only path temporary or isolated to a diagnostic case/script.
