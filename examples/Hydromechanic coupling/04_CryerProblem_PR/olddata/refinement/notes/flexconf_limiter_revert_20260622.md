# FlexibleConfinement limiter tests and revert, 2026-06-22

## Scope

This note records the recent Cryer FlexibleConfinement limiter tests before the
temporary output folders were cleaned. The implementation decision after these
tests is to use the global pair-wise Zhao-style kernel-truncation confinement
without free-surface or near-free-surface limiting.

The near-free-surface search routine is kept in the code as an inactive
diagnostic/development helper, but it is not called by default and is not linked
to the confinement force.

## Baseline without limiter

Previous diagnostics for the global pair-wise FlexibleConfinement showed:

- all fluid particles carried nonzero `HydroMechLoadAce`;
- the net spherical force residual was near zero;
- integrated signed inward equivalent pressure was about `1.17 q0`;
- about `96.3%` of the inward force was still located in the boundary band
  `r >= R - KernelSize`;
- about `3.6-3.7%` of the inward force remained in the nominal core;
- the `k=1e-5`, no-ramp, drainage-from-start short validation reached a
  numerical peak of about `1.2043 p0` at `T_v=0.048`, with early-window RMSE
  about `0.0402` against the corrected u-pw analytical solution.

Although this baseline is not perfect, it remained the best verified curve
among the tested loading variants.

## ZhaoFi / `posdiv` threshold route

The Zhao Eq.54-style `fi` route was tested by deriving a kernel-support index
from `posdiv`/free-surface tracking and using it as a confinement limiter.

Main observations:

- `fi <= 0.70` selected essentially one outer layer and produced only about
  `0.847` of the ramp target pressure.
- `fi <= 0.9228` selected about `23.74%` of particles and produced about
  `0.991` of the ramp target pressure.
- `fi <= 0.95` selected about `29.84%` of particles and produced about `1.106`
  times the ramp target.
- `fi <= 1.15` selected about `99.55%` of particles, reintroduced core loading,
  and produced about `1.168` times the ramp target.
- A pure `fi` threshold could not cleanly select every incomplete-support layer
  without also selecting most of the complete-support core.

Conclusion: this route is not robust enough for the current Cryer case. The
`ZhaoFi` output array and confinement connection were removed. `posdiv` remains
only as the original free-surface diagnostic value.

## Near-free-surface FSType limiter route

The DualSPHysics+-style near-free-surface limiter was tested by applying
FlexibleConfinement only to `FSType=1,2,3`:

- `FSType=2`: free surface;
- `FSType=1`: near free surface, roughly the three interior layers with
  incomplete kernel support;
- `FSType=3`: isolated.

The limiter behaved as intended geometrically:

- fluid particles: `22483`;
- free-surface particles: `3630` (`16.15%`);
- near-free-surface particles: `8447` (`37.57%`);
- active confinement particles: `12077` (`53.72%`);
- nonzero `HydroMechLoadAce` matched this active set exactly;
- core inward force fraction was zero;
- net force ratio was about `5.7e-4`.

However, the resulting equivalent confinement was still about `1.142 q0` and
the short `k=1e-5`, no-ramp, drainage-from-start comparison was worse than the
baseline:

- near-FS limiter peak was about `1.1544 p0` at `T_v=0.054`;
- early-window RMSE was about `0.139`, clearly worse than the no-limiter
  baseline RMSE of about `0.0402`;
- the peak was further below the corrected analytical peak.

Conclusion: the limiter correctly identifies the intended particle shell, but
it degrades the Cryer center pore-pressure evolution without an additional
normalization model. To avoid adding more empirical XML controls, this route is
kept inactive.

## Current code decision

- `HMLOAD_FlexibleConfinement` uses global pair-wise confinement again.
- No free/near-free-surface limiter is applied to FlexibleConfinement.
- Near-free-surface detection code remains present but disabled by default.
- The `ZhaoFi`/`posdiv` confinement route and output links were cleaned.
- Cryer should continue using `HydroMechTopLoadMode=3` for FlexibleConfinement,
  with no extra limiter or scale parameter.
