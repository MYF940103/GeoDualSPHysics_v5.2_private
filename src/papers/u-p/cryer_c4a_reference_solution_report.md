# Cryer C4-A Reference Solution Report

Date: 2026-05-12

## Objective

Implement an independent analytical/reference solution for Cryer's problem
before attempting strict geometry, loading, boundary source changes, or solver
runs.

No GenCase, CPU, GPU, or PartVTK run was performed. No source files were
modified.

## Formula Source

The implemented expression follows the PDF-checked transcription documented in
`cryer_c3b_analytical_reference.md`. The center pressure is:

```text
p_w(0,t) / p0 =
  eta * sum_j [ (sin(xi_j) - xi_j)
  / (eta*xi_j*cos(xi_j)/2 + (eta - 1)*sin(xi_j)) ]
  * exp(-xi_j^2*T_v)
```

with:

```text
(1 - eta*xi_j^2/2)*tan(xi_j) = xi_j
eta = (1 - nu)/(1 - 2*nu)
T_v = c_v*t/a^2
```

The script solves roots in the intervals `((j-1/2)pi, j*pi)`.

## Implemented Files

Directory:

`examples/u-pw/03_Cryer_Problem/strict_reproduction_plan/`

Key files:

- `cryer_reference_solution.py`
- `cryer_reference_curves.csv`
- `cryer_reference_roots.csv`
- `cryer_reference_convergence.csv`
- `cryer_reference_peak_metrics.csv`
- `cryer_reference_selfcheck.json`
- `fig7b_digitization_README.md`
- `figures/cryer_reference_center_pressure_curves.svg/png/pdf`
- `figures/cryer_reference_root_convergence.svg/png/pdf`
- `figures/cryer_reference_peak_vs_nu.svg/png/pdf`
- `figures/cryer_reference_long_time_decay.svg/png/pdf`

Command used:

```powershell
py ..\examples\u-pw\03_Cryer_Problem\strict_reproduction_plan\cryer_reference_solution.py --make-plot
```

## Root Solver and Residuals

Default settings:

- `nu = 0.1, 0.2, 0.3, 0.45`
- `T_v` range: `1e-4` to `10`
- `num_tv = 600`
- `num_roots = 200`

Diagnostics:

| Quantity | Value |
|---|---:|
| max absolute root residual | `1.116e-07` |
| max scaled root residual | `1.794e-10` |
| max curve difference, 100 roots vs 200 roots | `4.664e-05` |
| max curve difference, 50 roots vs 200 roots | `8.061e-02` |

The absolute residual is largest for high-index roots where the tangent equation
is ill-conditioned in double precision. The scaled residual is close to
`1e-10`, and the curve convergence shows that the default 200-root truncation
is appropriate for the selected `T_v >= 1e-4` range.

## Peak Response Metrics

| nu | peak `p_w(0,t)/p0` | peak `T_v` | pressure at `T_v=1e-4` | pressure at `T_v=10` |
|---:|---:|---:|---:|---:|
| 0.10 | `1.472754` | `5.793e-02` | `1.020198` | `1.220e-22` |
| 0.20 | `1.364251` | `5.263e-02` | `1.017000` | `1.167e-26` |
| 0.30 | `1.249008` | `4.600e-02` | `1.012911` | `2.412e-31` |
| 0.45 | `1.062769` | `3.448e-02` | `1.004080` | `6.226e-40` |

The reference curves show the expected Mandel-Cryer nonmonotonic center-pressure
response. The overshoot magnitude increases as Poisson ratio decreases, and all
curves decay toward zero at long time.

## Figure 7B Validation Data

No digitized Figure 7B data is currently available. The script therefore
generates analytical reference candidates and self-checks, but it does not yet
claim complete validation against the published plot.

Digitized input files can be added later using:

- `digitized_Fig7B_nu01.csv`
- `digitized_Fig7B_nu02.csv`
- `digitized_Fig7B_nu03.csv`
- `digitized_Fig7B_nu045.csv`

with columns:

```csv
Tv,normalized_center_pressure
```

When present, the script will write `cryer_reference_fig7b_validation.csv`.

## Readiness for Simulation Comparison

The script is ready to provide reference curves for future numerical
postprocessing, with these caveats:

- the curves should be described as PDF-transcribed analytical reference
  candidates until checked against Figure 7B/digitized data;
- `c_v` mapping to the current material constants must be confirmed before
  converting physical time to `T_v`;
- strict simulation should not begin until all-around spherical traction and
  drained curved boundary routes are decided.

## Next Step

Proceed to C4-B: audit whether native DualSPHysics/XML mechanisms can apply
all-around spherical traction `p0`. In parallel, collect or digitize Figure 7B
data for reference validation.
