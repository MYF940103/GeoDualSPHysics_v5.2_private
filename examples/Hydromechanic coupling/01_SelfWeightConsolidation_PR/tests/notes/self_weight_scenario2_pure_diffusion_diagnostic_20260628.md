# Scenario2 pure diffusion diagnostic, 2026-06-28

## Purpose

Check whether the late-time slow dissipation in Scenario2 comes mainly from the inherited Stage1 pore-pressure profile, or from the coupled hydromechanical update path.

## Method

- Added offline diagnostic script:
  - `tests/support/pure_diffusion_diagnostic_1d.py`
- The script reads existing `scenario2_profiles_by_tv.csv` and `scenario2_bottom_dissipation.csv`.
- It evolves the numerical initial excess pore-pressure profile with only the 1D diffusion equation.
- Boundary conditions:
  - bottom: no-flow
  - top: drained
- It does not update displacement, strain, effective stress, porosity, mDBC state, or Shepard filtering.
- Two initial states are compared:
  - `pure(SPH init)`: Stage1/restart numerical initial profile
  - `pure(ideal init)`: analytical undrained initial profile sampled at the same z layers

## Outputs

Baseline `SlipMode=1`:

- `tests/figures/CaseSWScenario2_restart_p0060_D_DTv0005_pure_diffusion/scenario2_pure_diffusion_diagnostic.png`
- `tests/figures/CaseSWScenario2_restart_p0060_D_DTv0005_pure_diffusion/scenario2_pure_diffusion_rms.png`
- `tests/figures/CaseSWScenario2_restart_p0060_D_DTv0005_pure_diffusion/scenario2_pure_diffusion_bottom_diagnostic.csv`
- `tests/figures/CaseSWScenario2_restart_p0060_D_DTv0005_pure_diffusion/scenario2_pure_diffusion_profile_diagnostic.csv`

Free-slip + `MDBCCorrector=0`:

- `tests/figures/CaseSWScenario2_restart_p0060_D_DTv0005_freeslip_mdbcc0_pure_diffusion/scenario2_pure_diffusion_diagnostic.png`
- `tests/figures/CaseSWScenario2_restart_p0060_D_DTv0005_freeslip_mdbcc0_pure_diffusion/scenario2_pure_diffusion_rms.png`
- `tests/figures/CaseSWScenario2_restart_p0060_D_DTv0005_freeslip_mdbcc0_pure_diffusion/scenario2_pure_diffusion_bottom_diagnostic.csv`
- `tests/figures/CaseSWScenario2_restart_p0060_D_DTv0005_freeslip_mdbcc0_pure_diffusion/scenario2_pure_diffusion_profile_diagnostic.csv`

## Key result

For both boundary-mode groups, the pure-diffusion result using the numerical SPH initial profile remains close to Terzaghi theory. The full coupled result is nearly identical to pure diffusion at early time, but increasingly lags at late time.

Free-slip + `MDBCCorrector=0` bottom excess pore pressure:

| Tv | theory kPa | pure(SPH init) kPa | full coupled kPa | full - pure kPa |
| --- | ---: | ---: | ---: | ---: |
| 0.100 | 6.9124 | 6.9908 | 6.9921 | 0.0013 |
| 0.500 | 2.5369 | 2.5679 | 2.6380 | 0.0701 |
| 1.000 | 0.7388 | 0.7478 | 1.0816 | 0.3338 |

Profile RMS for free-slip + `MDBCCorrector=0`:

| Tv | full-theory kPa | pure-theory kPa | full-pure kPa |
| --- | ---: | ---: | ---: |
| 0.100 | 0.0610 | 0.0588 | 0.0083 |
| 0.500 | 0.0687 | 0.0219 | 0.0468 |
| 1.000 | 0.2247 | 0.0064 | 0.2183 |

## Interpretation

The inherited initial pore-pressure profile is not the main cause of the late-time slow dissipation. If it were, the pure-diffusion run started from the same initial profile would also show a large late-time lag. Instead, pure diffusion almost collapses back to theory.

The remaining error is therefore more likely introduced by the coupled update path after the initial state:

- effective storage/compressibility used in the `u-pw` pore-rate update,
- volumetric-strain contribution interacting with stress relaxation,
- mDBC and Shepard interaction during the coupled run,
- or a mismatch between the Terzaghi consolidation coefficient and the actually realized coupled diffusion coefficient.

The previous equivalent-cv diagnostic already suggested an effective `cv/cv_ref` of about `0.95` globally and a stronger late-time lag. This pure-diffusion diagnostic shows that the lag is not explained by the initial profile alone.

## Suggested next check

Keep the current case data unchanged. The next targeted check should quantify the two terms in the pore-pressure-rate equation separately:

- compression term: `kwn*(-divv)`
- Darcy seepage term: `kwn*2*khyd*lapw/(rho_w*g)`

If the seepage term alone gives the correct decay but compression remains positive or under-dissipative late in the run, the issue is coupled volumetric strain / stress relaxation rather than hydraulic diffusion.
