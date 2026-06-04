# Stage 1 Boundary Diagnostic Summary

Date: 2026-06-03

Purpose: diagnose the bottom boundary layer observed in Stage 1 self-weight consolidation, where pore pressure is close to the expected profile but effective stress near the fixed bottom boundary is locally overestimated.

## Baseline Observation

Case: `CaseSelfWeightConsolidation_Stage1_out`, normal CPU code, `-mdbc`, `SoilStressRateGradCorr=0`.

- Bottom first fluid layer: `sigma_zz = -781.7 Pa`, analytical `sigma_zz = -82.4 Pa`.
- Bottom first 10 layers maximum absolute `sigma_zz` error: `699.3 Pa`.
- Bottom `0 < z < 0.1 m` RMS `sigma_zz` error: `297.3 Pa`.
- Core `0.1 < z < 0.85 m` RMS `sigma_zz` error: `0.58 Pa`.
- Core pore-pressure RMS error: `50.6 Pa`.

Conclusion: the Stage 1 stress field is excellent in the core, but the bottom fixed-boundary layer contains a local effective-stress artifact.

## Diagnostic 1: Skip Fixed-Boundary Neighbours in Stress-Rate Grad(v)

Temporary CPU patch: keep boundary force, density and viscosity contributions, but skip fixed-boundary neighbours only when accumulating velocity gradients for `grad(v) -> strain rate -> Rsigmac`.

Result at final Stage 1 time:

| case | bottom first 10 layers max `sigma_zz` error | core `sigma_zz` RMS | core pore RMS | max speed |
|---|---:|---:|---:|---:|
| skip fixed-boundary grad, `-mdbc` | `2.23e5 Pa` | `2424 Pa` | `13568 Pa` | `0.256 m/s` |
| skip fixed-boundary grad, `-mdbc_noslip` | `2.26e5 Pa` | `2423 Pa` | `13497 Pa` | `0.238 m/s` |

Conclusion: simply removing fixed-boundary neighbours from the stress-rate velocity-gradient operator is invalid. It destroys boundary support and causes rapid instability.

Action: the temporary code patch was reverted.

## Diagnostic 2: SlipMode=2 / No-Slip

Normal CPU code, comparing `-mdbc` (`SlipMode=1`) and `-mdbc_noslip` (`SlipMode=2`).

| case | bottom first 10 layers max `sigma_zz` error | core `sigma_zz` RMS | core pore RMS | max speed |
|---|---:|---:|---:|---:|
| normal `SlipMode=1` | `699.26 Pa` | `0.583 Pa` | `50.58 Pa` | `3.33e-5 m/s` |
| normal `SlipMode=2` | `699.26 Pa` | `0.583 Pa` | `50.56 Pa` | `3.34e-5 m/s` |

Conclusion: switching to no-slip does not improve this 1D Stage 1 boundary layer. The artifact is dominated by the normal fixed-boundary constraint/stress-rate path, not the tangential slip mode.

## Diagnostic 3: CPU Stress-Rate Gradient Correction

Implemented CPU support for the already existing `SoilStressRateGradCorr` parameter, following the GPU logic:

- pass `CorrMatc` into CPU interaction parameters;
- apply the kernel-gradient correction matrix to the three velocity-gradient rows before computing strain/spin rate;
- only active when `SoilStressRateGradCorr=1`.

Result:

| case | bottom first 10 layers max `sigma_zz` error | core `sigma_zz` RMS | core pore RMS | max speed |
|---|---:|---:|---:|---:|
| `SoilStressRateGradCorr=0` | `699.26 Pa` | `0.583 Pa` | `50.58 Pa` | `3.33e-5 m/s` |
| `SoilStressRateGradCorr=1` | `701.12 Pa` | `0.683 Pa` | `49.68 Pa` | `3.32e-5 m/s` |

Conclusion: the standard kernel-gradient correction is active on CPU but does not reduce the bottom effective-stress layer. This suggests the artifact is not a generic gradient-consistency error.

## Interpretation

The bottom boundary stress seen in visualization can be larger than the nearby fluid/ghost stress because current mDBC stress handling uses first-order extrapolation:

1. reconstruct stress and stress gradient at the ghost node from nearby fluid particles;
2. extrapolate back to the boundary particle using `sigma_boundary = sigma_ghost + grad(sigma) dot dpos`.

If the first fluid layer already contains a stress spike, the first-order mDBC extrapolation can propagate or amplify it into boundary particles.

## Recommended Next Step

For the 1D self-weight consolidation verification, use analytical initialization of both effective stress and pore pressure instead of relying on dynamic Stage 1 prestress loading.

This avoids the fixed-bottom boundary layer and gives a clean initial condition for Stage 2 consolidation verification.

