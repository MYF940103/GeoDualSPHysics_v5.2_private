# T4o Cap-Support-Preserving Transition Rationale

## Objective

T4n2 showed that restart is not the immediate blocker. The Stage A
all-surface `f_i` confinement state was restored exactly into Stage B, including
position, velocity, density, `Sigma_kk`, `Sigma_ij`, `Kplastic`, and
`PorePress`. The failure occurred after the restarted state was changed from
all-surface confinement to lateral-only confinement.

T4o tests the next mechanical hypothesis: a triaxial specimen should not lose
all top/bottom hydrostatic support after isotropic confinement. During axial
loading, lateral confinement remains, the caps still provide axial reaction,
and the imposed axial compression should be an additional deviatoric action
superposed on the confined state.

## Why Restart Is Not The Blocker

The T4n2 continuity comparison gave zero saved-precision differences for the
restarted particle state:

- position;
- velocity;
- density;
- stress tensor components;
- `Kplastic`;
- `PorePress`.

This means the all-surface Stage A state can be carried into a second stage
without losing the current elastic u-pw fields. `ExcessPorePress` is not
separately restored, but the current tests use `HydraulicElevationSource=0`, so
`ExcessPorePress` is equivalent to `PorePress`.

## Why The Lateral-Only Switch Fails

Stage A all-surface confinement applies the Zhao-style stress-like confinement
term to all low-`f_i` free-surface regions: lateral surface, caps, and edge
rings. Switching immediately to lateral-only confinement removes cap and edge
support while the particle stress state is still close to hydrostatic.

The result is a mechanical mismatch:

- top/bottom support is removed;
- the lateral surface remains loaded;
- cap and edge regions unload differently from the lateral surface;
- the hydrostatic stress state turns deviatoric;
- `q` rises and `p'` drifts away from the target.

In T4n2 this reduced but did not eliminate the imbalance: the restarted
lateral-only case ended with `p' approx 13.50 Pa` and `q approx 37.89 Pa`, still
far from the Stage A state (`p' approx 46.38 Pa`, `q approx 15.65 Pa`).

## Why Cap Support Should Not Be Removed Abruptly

The initial hydrostatic stress created in T4k/T4m is three-dimensional:
`sigma'_xx = sigma'_yy = sigma'_zz = -50 Pa` in the current compression-negative
stress convention. Removing axial support after Stage A is equivalent to
removing the external balance for `sigma'_zz` while retaining lateral support
for `sigma'_xx` and `sigma'_yy`.

For triaxial loading, the axial path should be interpreted as:

1. establish isotropic confinement;
2. keep lateral confinement during shear/compression;
3. keep cap reaction/support available;
4. add axial deviatoric loading on top of the confined state.

This is different from setting the caps completely unsupported at the start of
Stage B.

## T4l And T4m Trade-Off

T4l introduced explicit `CapConfiningStress`, which improved the center-core
pore pressure relative to lateral-only support. However, it mixed two different
surface mechanisms:

- lateral surface: Zhao-style flexible kernel-truncation confinement;
- caps: explicit normal support applied to cap target particles.

T4m showed that all-surface `f_i` confinement is more internally consistent for
isotropic pre-equilibrium. It lowered the final `q` proxy to about `15.6 Pa`,
compared with about `53.5 Pa` in the lateral+cap mixed route.

## T4o Hypothesis

The T4o hypothesis is therefore narrow:

- use all-surface `f_i` confinement for Stage A isotropic equilibrium;
- restart from the Stage A state;
- retain lateral confinement plus explicit cap support in Stage B;
- test whether cap support preserves the hydrostatic state better than the
  T4n2 lateral-only restart.

The test is diagnostic. If Stage B remains imbalanced, the blocker is not the
restart or lack of cap support alone, but the discrete mismatch between
all-surface Zhao confinement and the explicit cap/lateral support mechanism.
