# T4l Full Hydrostatic Confinement Report

## Summary

T4l adds a CPU-only cap-normal hydrostatic support route and tests whether the
T4k initial effective stress can be externally balanced before axial loading.
The new interface works and improves the feedback-off confinement state, but the
full-feedback confinement gate still fails. Axial loading, DP, MCC, and GPU
simulation remain deferred.

## Source Change

`CapConfiningStress=1` applies balanced top/bottom cap-normal support:

```text
F_cap = p0_eff * pi * R^2
```

The top cap receives acceleration along `-axis`; the bottom cap receives
acceleration along `+axis`. Edge-ring particles are skipped to avoid
double-counting the lateral `FlexibleConfiningStress` route. Defaults remain
off and legacy behavior is unchanged. GPU execution hard-errors when the cap
support is enabled.

## Cases

All cases used `SoilConstitutiveModel=0`, `InitialStressMode=1`,
`InitialEffectiveStressIso=50 Pa`, selected lateral confinement, no axial
loading, and CPU Release.

| Case | Cap support | Feedback | Code | Excluded | DtMin | Max `PorePressRate` |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| Current mismatch | off | off | 0 | 0 | 0 | `4.48e7 Pa/s` |
| Full support | on | off | 0 | 0 | 0 | `4.42e7 Pa/s` |
| Full support | on | delayed | 0 | 0 | 0 | `1.16e12 Pa/s` |

`Kplastic` stayed `0` in all cases.

## Feedback-Off Improvement

Cap support changes the confinement-only feedback-off state substantially:

| Metric | Lateral-only | Full support |
| --- | ---: | ---: |
| final center pore pressure | `-10993 Pa` | `-62.9 Pa` |
| final specimen mean pore pressure | `-14223 Pa` | `-4494 Pa` |
| final `p'` proxy | `17.1 Pa` | `38.9 Pa` |
| final `q` proxy | `51.5 Pa` | `53.5 Pa` |

The center-core pressure response is much closer to balanced after cap support,
and the cap diagnostics are symmetric:

- top targets: `18`;
- bottom targets: `18`;
- edge-ring skipped: `112`;
- top/bottom acceleration mean: about `3.01 m/s2` during the logged ramp frame;
- cap symmetry residual: `0`.

This confirms that T4k failed partly because the initialized hydrostatic stress
had no matching axial cap traction.

## Remaining Failure

Full support does not yet produce a stable coupled u-pw equilibrium. When
delayed feedback is enabled:

- max velocity reaches `35.97 m/s`;
- max `DivVel` reaches `1741.775`;
- max `PorePressRate` reaches `1.16e12 Pa/s`;
- all particles still experience negative pressure at some point;
- final `p'` and `q` proxies are far from hydrostatic.

The run remains numerically clean in the narrow `code/excluded/DtMin` sense, but
it fails the physical stability gate. Therefore axial loading was not run.

## Hydrostatic State

The hydrostatic state is improved but not maintained. Full cap+lateral support
raises the final mean `p'` proxy toward the `50 Pa` target, but the nonzero `q`
proxy and remaining specimen-wide negative pore pressure show that this reduced
free-surface cylinder is still not a validated hydrostatic equilibrium state.

## Answers To T4l Gate Questions

1. T4k failed because initial hydrostatic effective stress was paired with
   lateral-only external traction; the `sigma_zz` support was missing.
2. Cap normal support is implemented as an opt-in CPU-only feature.
3. Feedback-off full hydrostatic support is numerically stable and improves the
   center-core response.
4. Feedback-on/delayed full hydrostatic support is not stable.
5. Negative pressure and reversal are improved in the feedback-off center core
   but not eliminated globally.
6. `PorePressRate` is not improved once full feedback is restored.
7. The stress state is not yet acceptably hydrostatic; `q` remains significant.
8. Axial loading should not be restored yet.
9. DP and MCC remain deferred.
10. GPU remains deferred.

## Next Recommendation

Do not enter a T4m axial-loading baseline yet. The next step should refine the
hydrostatic equilibrium route itself: either improve cap/support distribution
and boundary completion, or move to a restart-based equilibrium stage with
explicit checks that the full-feedback confinement-only state remains stable
before axial loading.
