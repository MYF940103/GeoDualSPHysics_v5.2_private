# Lian Flexible Strip Sensitivity Conclusions - 2026-07-21

Case: `05_LianFlexibleStrip2D_PR`

This note preserves the conclusions from the latest short sensitivity runs before
removing generated test outputs, logs, figures, and diagnostic XML copies.

## Compared Runs

Common setup unless noted otherwise:

- Mixed mechanical wall behavior through `special/mdbcslip`: side walls
  free-slip and bottom wall fixed/no-slip.
- `TimeMax=3.0 s`, `TimeOut=0.05 s`.
- Zero gravity, so the stored pore pressure is equivalent to excess pore water
  pressure in this case.
- Default damping is `SoilDampingCoef=0.04`.

Variants:

- Baseline: `PoreMdbcInterpolationMode=0`, `DtFixed=1e-5`,
  `SoilDampingCoef=0.04`.
- MLS pore mDBC: `PoreMdbcInterpolationMode=1`.
- Low damping: `SoilDampingCoef=0.02`.
- High damping: `SoilDampingCoef=0.08`.
- Smaller timestep: `DtFixed=5e-6`.

## Main Result At t ~= 2.95 s

The `DtFixed=1e-5` short runs stopped with the last saved output at
`t=2.950010 s`; the smaller timestep run saved `t=2.950005 s` and also an
approximately exact `t=3.000005 s` frame.

| Variant | Time (s) | Max EPWP (kPa) | Mean EPWP (kPa) | P95 EPWP (kPa) | Area EPWP >= 1.5 kPa | Front x (m) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Baseline | 2.950010 | 2.118891 | 0.626636 | 1.944052 | 14.201% | 4.700 |
| MLS pore mDBC | 2.950010 | 2.121075 | 0.626827 | 1.945618 | 14.226% | 4.700 |
| Damping 0.02 | 2.950010 | 2.214633 | 0.646451 | 2.018885 | 15.162% | 5.000 |
| Damping 0.08 | 2.950010 | 2.001024 | 0.601076 | 1.850473 | 12.837% | 4.300 |
| DtFixed 5e-6 | 2.950005 | 2.116667 | 0.626516 | 1.942316 | 14.201% | 4.700 |

## Pairwise Conclusions

- `PoreMdbcInterpolationMode=1` has negligible influence on the pore-pressure
  field in this case. Its mean absolute difference from the baseline was about
  `0.000603 kPa`, with maximum absolute difference about `0.004606 kPa`.
- Reducing `DtFixed` from `1e-5` to `5e-6` also has negligible influence. The
  mean absolute difference from the baseline was about `0.000420 kPa`, with
  maximum absolute difference about `0.004195 kPa`.
- At exact 3 s, the `DtFixed=5e-6` result and the previous `LianMkSlipT5`
  baseline differed by only about `0.000417 kPa` in mean absolute error and
  `0.004289 kPa` in maximum absolute error.
- Damping controls the amplitude and spatial extent: `0.02` increases the field,
  while `0.08` reduces it. This is a sensitivity effect, not yet evidence that
  damping should be used to tune the benchmark away from the Lian default
  `0.04`.

## Decision For The Next Full Run

- Keep `SoilDampingCoef=0.04` for the formal long run.
- Keep `PoreMdbcInterpolationMode=0`, because MLS direct did not materially
  improve the 3 s pore-pressure field.
- Keep `DtFixed=1e-5`, because the short comparison is effectively timestep
  converged for this output.
- The remaining difference from Lian 2023 is more likely linked to the strip
  drainage/contact interpretation, the mixed mechanical wall behavior, or the
  formulation-level difference from the reference TPI/u-pw implementation than
  to `PoreMdbcInterpolationMode` or timestep size.

## Full Run Status

After recording the conclusions above, the generated contents of
`tests/configs`, `tests/outputs`, `tests/logs`, and `tests/figures` were removed.

A new full GPU run was then executed with the root case files:

- Output directory: `CaseLianFlexibleStrip2D_PR_out`.
- Solver command: GPU, mDBC free-slip command flag, `TimeMax=50`,
  `TimeOut=0.05`, `DtFixed=1e-5`.
- Confirmed XML parameters: `SoilDampingCoef=0.04`, `DtIni=1e-5`,
  `DtFixed=1e-5`, `TimeMax=50.0`, `TimeOut=0.05`.
- Solver result: finished with `code=0`.
- Excluded particles: `0`.
- Saved binary parts: `1000`, from `Part_0000` to `Part_0999`
  (`Part_0999` at `t=49.950010 s`).
- VTK post-processing: `1000` fluid VTK files and `1000` boundary VTK files
  written successfully.
- Output size after post-processing: about `4.67 GB`.

The final frame is `49.950010 s` rather than exactly `50.0 s`; this matches the
same output-scheduling behavior observed in the short runs when the next
`TimeOut` frame would pass `TimeMax`.
