# Softening Micro Tests

These cases verify the CPU-only Drucker-Prager exponential softening switch in
a tiny reduced slope geometry before using it in the main retrogressive slope
smoke.

They are not paper-scale reproduction cases.

## Cases

| Case | Purpose |
|---|---|
| `CaseRetrogressiveSlope_PR_SofteningMicro_Off` | Backward-compatible weak material smoke with `Softening=0`. |
| `CaseRetrogressiveSlope_PR_SofteningMicro_On` | Same weak material with `Softening=1`; stable no-plastic short check. |
| `CaseRetrogressiveSlope_PR_SofteningMicro_ExtremeResidual` | Residual-strength floor check with stronger softening coefficients. |
| `CaseRetrogressiveSlope_PR_SofteningMicro_Trigger` | Very weak short run designed to trigger plastic strain and visible cohesion degradation. |

## Latest Results

All four cases completed on CPU Release with:

- GenCase `code=0`;
- DualSPHysics `code=0`;
- excluded particles `0`;
- no NaN/Inf in `PartCsv` output.

The trigger case produced:

- `Kplastic_max = 8.5393706e-4`;
- estimated local cohesion minimum `0.8587 Pa` from `c = c_r + (c_p-c_r) exp(-n_coh Kplastic)`;
- `velocity_max = 4.667e-2 m/s`.

The non-trigger micro cases kept `Kplastic=0`, which is expected for their very
short, mild response. They are retained as stability and switch-regression
checks.

Generated solver output is removed after recording the `*_summary.csv` files.
