# q0 k=1e-4 dp=0.025 short resolution test to Tv=0.1, 2026-07-14

## Correction after review

This run is invalid as a resolution point. The case was generated in the root
case folder first and its geometry did not preserve the intended periodic
column width. After the user pointed out that the q0 Terzaghi case uses lateral
periodic boundaries, the generated output was rechecked:

- `dp=0.02`: `PeriodicXinc=(-0.1,0,0)`.
- This `dp=0.025` run: `PeriodicXinc=(-0.2,0,0)`.

The `dp=0.025` generated boundary particles also included an unintended top/side
row:

```text
z -0.0875 x [0.0125, 0.0375, 0.0625, 0.0875]
z -0.0625 x [0.0125, 0.0375, 0.0625, 0.0875]
z -0.0375 x [0.0125, 0.0375, 0.0625, 0.0875]
z -0.0125 x [0.0125, 0.0375, 0.0625, 0.0875]
z  1.2125 x [-0.0875, -0.0625, -0.0375, -0.0125]
```

Therefore the large error below is not evidence that a valid periodic
`dp=0.025` Terzaghi model fails. It is evidence that this generated XML produced
an invalid geometry/periodic span and must not be used for convergence.

The files were subsequently moved under `tests/` so test artifacts are no
longer left in the case root.

Purpose: test an intermediate coarse resolution between `dp=0.03` and `dp=0.02`
for the q0 Terzaghi case, then compare the `Tv=0.05` normalized L2 error with
the existing `dp=0.02`, `dp=0.01`, and `dp=0.005` results.

## Case

- XML: `tests/configs/resolution/CaseTerzaghiConsolidation_q0_PR_full_k1em4_dp0025_Tv01_Def.xml`
- BAT archive: `tests/configs/resolution/xCaseTerzaghiConsolidation_q0_PR_full_k1em4_dp0025_Tv01_win64_CPU.bat`
- Output: `tests/outputs/resolution/CaseTerzaghiConsolidation_q0_PR_full_k1em4_dp0025_Tv01_out`
- Run logs: `tests/logs/resolution/CaseTerzaghiConsolidation_q0_PR_full_k1em4_dp0025_Tv01_run.*.log`
- CPU executable: `DualSPHysics5.2CPU_win64.exe`
- `Dp=0.025`
- `DtFixed=1e-5`
- `TimeMax=3.65471428571429`
- `TimeOut=0.182185714285714`
- Fluid particles: `160`
- Fixed boundary particles: `20`
- PartVTK output: `PartFluid_0000.vtk` through `PartFluid_0020.vtk`

The run finished with `code=0` and `Excluded particles=0`. The final two output
intervals were much slower than the earlier intervals:

```text
Part_0019      3.461530        346153    18218    1745.96
Part_0020      3.643720        364372    18219    2611.26
Excluded particles...............: 0
Finished execution (code=0).
```

## Generated comparison files

Generated under:

`tests/figures/resolution_k1em4_dp0025_tv01_compare`

- `resolution_k1em4_dp0025_tv01_summary.csv`
- `resolution_k1em4_dp0025_tv01_targets.csv`
- `resolution_k1em4_dp0025_tv01_profiles_data.csv`
- `resolution_k1em4_dp0025_tv01_profiles.png`
- `resolution_k1em4_dp0025_tv01_l2_error.png`

## Tv=0.05 comparison

| dp | normalized L2 | U_num | U_theory | max speed |
| ---: | ---: | ---: | ---: | ---: |
| 0.025 | 0.9999999 | 0.9999999 | 0.2516198 | 1.5239e-4 |
| 0.02 | 0.0055486 | 0.2526910 | 0.2516198 | 2.5868e-4 |
| 0.01 | 0.0029535 | 0.2512471 | 0.2516198 | 2.5732e-4 |
| 0.005 | 0.0024876 | 0.2510134 | 0.2516198 | 2.5963e-4 |

The `dp=0.025` result is not a valid improvement or failure point relative to
`dp=0.03`; it is an invalid-geometry run. The numerical degree of consolidation
is almost exactly `1` at `Tv=0.05`, meaning the excess pore pressure is nearly
zero throughout the column, but this follows from the malformed periodic span
and unintended free-surface/drainage classification.

## FSType check

At `PartFluid_0010.vtk`:

- `dp=0.025`: `FSType=2` for 82/160 particles, `FSType=0` for 78/160 particles.
- `dp=0.02`: `FSType=2` for 5/250 particles, matching the top drained row.
- `dp=0.03`: `FSType=2` for 3/99 particles at this snapshot.

At the initial `dp=0.025` snapshot, the lateral columns are already marked as
free surface:

```text
xcol 0: FSType=2 for 40/40
xcol 1: FSType=0 for 39/40, FSType=2 for 1/40
xcol 2: FSType=0 for 39/40, FSType=2 for 1/40
xcol 3: FSType=2 for 40/40
```

Because the drainage boundary is `FreeSurface`, those side-column particles are
treated as drained particles once drainage starts. With `KernelSize=0.09` and
model width `0.1`, the drained side columns are inside the kernel support of the
remaining interior columns, so the whole column is numerically drained almost
immediately.

## Conclusion

This `dp=0.025` run should be excluded from convergence fits because it is not
the intended periodic geometry.

For this benchmark, the reliable early-time resolution comparison remains:

- `dp=0.02`
- `dp=0.01`
- `dp=0.005`

If a `dp=0.025` point is still needed, first regenerate the case under
`tests/configs/resolution` and verify from the GenCase/DualSPHysics logs that:

- `PeriodicXinc=(-0.1,0,0)`.
- Boundary particles remain bottom-only, matching the valid `dp=0.02` topology.
- The initial `FSType=2` particles are limited to the drained top row.
