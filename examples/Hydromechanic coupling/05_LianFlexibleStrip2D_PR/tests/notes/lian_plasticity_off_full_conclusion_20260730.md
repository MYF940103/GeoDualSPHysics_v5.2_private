# Lian flexible strip plasticity-off full-run check, 2026-07-30

## Purpose

Check whether the late-time excess pore-pressure residual in the Lian 2023 flexible strip case is caused by Drucker-Prager plastic yielding or return mapping.

## Temporary diagnostic patch

For this diagnostic run only, the CPU/GPU elastoplastic constitutive functions were temporarily forced to take the elastic branch immediately after the DP yield function evaluation:

- `source/JSphCpu.cpp`: `ConsRelationEP_fast()` and `ConsRelationEPsft_fast()`
- `source/JSphGpuSimple_ker.cu`: `ConsRelationEP_fast()` and `ConsRelationEPsft_fast()`

The temporary marker was `DSPH_TMP_DISABLE_PLASTICITY_DIAG`. It was removed after the run, and both CPU Debug and GPU Release were rebuilt successfully.

## Run

- Case: `05_LianFlexibleStrip2D_PR`
- Variant: `plasticoff_full_20260729`
- Output: `tests/outputs/CaseLianFlexibleStrip2D_PR_plasticoff_full_20260729_out`
- Solver log: `tests/logs/run_plasticoff_full_20260729_solver.log`
- Main options: `-DtFixed 0.00001 -TimeMax 50 -TimeOut 0.05 -PoreDtSafety 0.1`
- Solver result: finished with code 0
- Steps: 5,000,000
- Part files: 1000
- Excluded particles: 0

## Binary comparison against baseline

Compared against:

`CaseLianFlexibleStrip2D_PR_out/data`

Result:

`checked=1000 missing=0 mismatches=0`

All stored `Part_*.bi4` files are byte-for-byte identical between the baseline elastoplastic executable and the temporary plasticity-off executable.

## Conclusion

Disabling DP plastic correction produces no change in the full Lian flexible strip result. Therefore the late-time pore-pressure over-residual/slow dissipation in this case is not caused by plastic yielding or return mapping.

The current issue should continue to be debugged in the elastic hydromechanical paths: pore-pressure diffusion/permeability scaling, compression/strain-rate source term, drainage/free-surface mask, mDBC hydraulic boundary handling, and damping/time-integration coupling.

Adding a formal XML switch for elastic versus elastoplastic behavior can still be useful later as a model-selection feature, but it is not indicated as the fix for the present Lian late-time residual error.
