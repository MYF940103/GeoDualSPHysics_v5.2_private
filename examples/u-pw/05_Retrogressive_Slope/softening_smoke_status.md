# Softening Smoke Status: Retrogressive Slope

Date: 2026-05-11

## Cases

| Case | Purpose |
|---|---|
| `CaseRetrogressiveSlope_PR_SofteningSmoke_Off` | Reduced slope comparison with `Softening=0`. |
| `CaseRetrogressiveSlope_PR_SofteningSmoke` | Reduced slope comparison with `Softening=1`. |

The geometry is the same small reduced wedge used for the earlier PR smoke.
The strength parameters preserve the paper's sensitive-clay ratio and
softening coefficient, but cohesion is additionally scaled down so plasticity is
visible within a short CPU smoke:

- `phi = phi_r = 0 deg`;
- `coh = 151 Pa`;
- `coh_r = 15 Pa`;
- `n_coh = n_phi = 5`;
- `TimeMax = 0.002 s`.

This is not a paper-scale reproduction.

## Execution

| Check | Result |
|---|---|
| GenCase | code=0 for both cases |
| DualSPHysics CPU Release | code=0 for both cases |
| Excluded particles | 0 for both cases |
| NaN/Inf | none detected |
| Frames | 2 |
| Key fields | `PorePress`, `ExcessPorePress`, `PorePressRate`, `DivVel`, `LapPorePress`, `LapZ`, `Kplastic`, `PorePressureAccelDiff.*` |

## Summary

| Case | Softening | Kplastic max | estimated cohesion min | max displacement | max velocity |
|---|---:|---:|---:|---:|---:|
| Off | 0 | `6.5801572e-4` | `151.0 Pa` | `1.59078e-4 m` | `6.185e-1 m/s` |
| On | 1 | `6.5801572e-4` | `150.553 Pa` | `1.59078e-4 m` | `6.185e-1 m/s` |

The short smoke confirms that the reduced slope can run with the CPU
softening path enabled and that the postprocessor computes local degraded
cohesion from `Kplastic`. The physical response is still almost identical over
this tiny window; full retrogression requires longer GPU-scale runs, calibrated
initial state, and production material/boundary choices.

Generated solver output was removed after the summary CSV files were saved.
