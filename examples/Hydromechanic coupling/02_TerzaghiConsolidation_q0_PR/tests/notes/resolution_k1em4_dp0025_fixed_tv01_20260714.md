# q0 k=1e-4 corrected dp=0.025 short resolution test to Tv=0.1, 2026-07-14

Purpose: rerun the `dp=0.025` q0 Terzaghi resolution check after the first
attempt produced an invalid periodic span.

## Files

- XML: `tests/configs/resolution/CaseTCq0_res_k1em4_dp0025_fix_Tv01_Def.xml`
- BAT: `tests/xCaseTCq0_res_k1em4_dp0025_fix_Tv01_win64_CPU.bat`
- Output: `tests/outputs/resolution/CaseTCq0_res_k1em4_dp0025_fix_Tv01_out`
- Logs: `tests/logs/resolution/CaseTCq0_res_k1em4_dp0025_fix_Tv01_run.*.log`
- Comparison data: `tests/figures/resolution_k1em4_dp0025_fix_tv01_compare`

## Geometry and run checks

The corrected GenCase output is valid for the intended periodic Terzaghi column:

- `Fixed=16`
- `Fluid=160`
- Initial particle limits: `X=0.0125..0.0875`, `Z=-0.0875..0.9875`
- No unintended top/side boundary row
- `PeriodicXinc=(-0.1000000000000001,0,0)`
- `Excluded particles=0`
- Solver finished with `code=0`
- PartVTK wrote `PartFluid_0000.vtk` through `PartFluid_0020.vtk`

## FSType check

The corrected run keeps only the top row drained/free-surface:

```text
PartFluid_0000: FSType {0: 156, 2: 4}
PartFluid_0010: FSType {0: 156, 2: 4}
PartFluid_0020: FSType {0: 156, 2: 4}
```

Each of the four lateral columns has exactly one `FSType=2` particle at the top.
There is no side-column free-surface contamination.

## Tv=0.05 and Tv=0.1 comparison

| dp | Tv | normalized L2 | U_num | U_theory | max speed |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0.025 | 0.05 | 0.0074380 | 0.2536342 | 0.2516198 | 2.5991e-4 |
| 0.02 | 0.05 | 0.0055486 | 0.2526910 | 0.2516198 | 2.5868e-4 |
| 0.01 | 0.05 | 0.0029535 | 0.2512471 | 0.2516198 | 2.5732e-4 |
| 0.005 | 0.05 | 0.0024876 | 0.2510134 | 0.2516198 | 2.5963e-4 |
| 0.025 | 0.1 | 0.0064012 | 0.3577840 | 0.3563335 | 1.8813e-4 |
| 0.02 | 0.1 | 0.0049371 | 0.3569035 | 0.3563335 | 1.8638e-4 |
| 0.01 | 0.1 | 0.0031265 | 0.3554914 | 0.3563335 | 1.8337e-4 |
| 0.005 | 0.1 | 0.0032031 | 0.3570826 | 0.3563335 | 2.5581e-3 |

## Conclusion

The corrected `dp=0.025` point behaves consistently as a coarse valid resolution
point. It is worse than `dp=0.02` but no longer catastrophically wrong. The first
`dp=0.025` run should remain classified as invalid because its periodic span was
`-0.2` and its geometry included an unintended top/side boundary row.
