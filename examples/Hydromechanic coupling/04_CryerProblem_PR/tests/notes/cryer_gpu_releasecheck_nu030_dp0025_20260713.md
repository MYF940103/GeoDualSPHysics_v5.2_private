# Cryer GPU release check, nu030 dp=0.0025, 2026-07-13

Purpose: test whether the current rebuilt GPU Release improves the existing
formal Cryer `dp=0.0025`, `nu=0.3`, `k=1e-5` result before spending time on the
remaining Poisson-ratio groups.

## Setup

- Source/exe: current rebuilt GPU Release, `DualSPHysics5.2_GEO_win64.exe`.
- Base XML: `CaseCryerProblem_PR_Def.xml`.
- Test XML: `tests/configs/gpu_releasecheck/CaseCryerProblem_PR_gpu_releasecheck_nu030_Def.xml`.
- Test BAT: `tests/xCaseCryerProblem_PR_gpu_releasecheck_nu030_win64_GPU.bat`.
- Output: `tests/outputs/gpu_releasecheck/CaseCryerProblem_PR_gpu_releasecheck_nu030_out`.
- Postprocess: `support/postprocess_cryer.py`, with `CRYER_TV_MIN=0.001` and
  center sample radius `r <= 1dp = 0.0025 m`.
- PartVTK variables omitted `+hydromechloadace`; only the needed pressure and
  state fields were exported.

Runtime log confirmed:

```text
Hydromechanics="Enabled"
Boundary="DBC"
TimeMax=0.910928571429
TimePart=0.000910928571429
Finished execution (code=0).
```

## Result

Comparison against the retained old formal `nu=0.3`, `dp=0.0025` metrics in
`figures/formal_validation/cryer_poisson_sweep_center_r1dp_metrics.json`:

| Metric | Old formal | New GPU release check | Change |
| --- | ---: | ---: | ---: |
| RMSE | 0.0227609 | 0.0225730 | -0.0001879 |
| MAE | 0.0179022 | 0.0176827 | -0.0002195 |
| SPH peak p/q0 | 1.2159517 | 1.2157688 | -0.0001829 |
| SPH value at theory-peak Tv | 1.2148734 | 1.2146684 | -0.0002050 |
| Theory peak p/q0 | 1.2490075 | 1.2490075 | 0 |
| Final p/q0 | 0.0042874 | 0.0030289 | -0.0012585 |

The global RMSE and late-time final value improve slightly, but the main Cryer
peak amplitude does not improve; the SPH value at the theoretical peak is very
slightly lower than the old formal run.

## Conclusion

The current rebuilt GPU Release does not materially improve the existing
`dp=0.0025`, `nu=0.3` Cryer validation. Since the main peak deficit is not
recovered, the remaining Poisson-ratio groups were not rerun.
