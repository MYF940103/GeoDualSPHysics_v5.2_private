# C5l Radial Operator Audit Report

## Objective

C5l is a postprocessing-only audit of the pressure-only strict Cryer drained
sphere. It does not modify source, does not run GPU, does not run Cryer
compression, and does not add another boundary mode.

Artifacts are retained under:

`examples/u-pw/03_Cryer_Problem/strict_reproduction_plan/C5l_RadialOperatorAudit/`

The audit has two parts:

- a manufactured radial-field test on reconstructed static sphere clouds;
- a shell storage / inter-shell exchange audit using retained C5i, C5j, and
  C5k pressure-only diffusion CSVs.

## Source Formula Audited

The material-material `LapPorePress` operator in the CPU path is a Morris-type
pair Laplacian:

```text
Lap_i += 2 * V_j * (p_i - p_j) * (r_ij dot grad W_ij) / (|r_ij|^2 + eps)
```

C5l audits this material-only operator separately from the extra curved drained
boundary contributions. Boundary modes `4`, `5`, and `6` are then interpreted
through retained pressure-only shell data.

## Manufactured-Field Results

The static clouds match the committed C5h/C5i sphere metrics:

| dp | material particles | surface roughness std | boundary pairs |
|---:|---:|---:|---:|
| `0.010` | `739` | `0.003577` | `194490` |
| `0.008` | `1213` | `0.003033` | `315386` |
| `0.0065` | `2601` | `0.003647` | `650052` |

Constant field:

- `u=1` gives exactly zero material-only Laplacian residual for all three
  reconstructed clouds.

Quadratic radial field:

- for `u=r^2`, exact `nabla^2 u=6`;
- interior consistency is good and improves at `dp=0.0065`:
  - `dp=0.010`: interior RMSE `1.056`;
  - `dp=0.008`: interior RMSE `1.074`;
  - `dp=0.0065`: interior RMSE `0.112`;
- near-boundary consistency is poor and non-convergent:
  - `dp=0.010`: near-boundary p95 error `12.24`, bias `-11.18`;
  - `dp=0.008`: near-boundary p95 error `14.06`, bias `-13.02`;
  - `dp=0.0065`: near-boundary p95 error `17.08`, bias `-13.68`.

The same pattern appears for the drained-like gap field `u=R-r`: the largest
errors are near the outer shell, with p95 error rising from about `100` to
`122` to `145` as the tested cloud moves from `dp=0.010` to `0.008` to
`0.0065`.

## Shell-Exchange Audit

The shell balance uses retained pressure-only outputs and checks:

```text
dS_k/dt + F_{k+1/2} - F_{k-1/2}
```

where `F` is reconstructed from radial finite-volume gradients between shell
means and the drained value at `R`.

Normalized p95 shell residuals are:

| case | normalized residual p95 |
|---|---:|
| mode 4 normalized, `dp=0.010` | `0.866` |
| mode 4 normalized, `dp=0.008` | `0.873` |
| mode 4 normalized, `dp=0.0065` | `1.213` |
| mode 5 MLS, `dp=0.008` | `0.919` |
| mode 5 MLS, `dp=0.010` | `0.887` |
| mode 6 shell, `dp=0.008` | `1.302` |
| mode 6 shell, `dp=0.010` | `0.958` |

The `dp=0.0065` normalized mode-4 case and the C5k `dp=0.008` mode-6 case are
the least shell-consistent among the retained pressure-only gates. This agrees
with the observed late flux reversals and pressure-rate spikes.

## Why dp=0.0065 Got Worse

The `dp=0.0065` cloud improves the deep interior manufactured quadratic test,
but it worsens the near-boundary audit:

- surface roughness is not monotonic: `0.003033` at `dp=0.008` becomes
  `0.003647` at `dp=0.0065`;
- max surface radius error increases to about `0.00741 m`;
- material-boundary pair count grows to `650052`;
- near-boundary quadratic p95 error rises to `17.08`;
- shell residual p95 rises to `1.213` of the median boundary flux for the
  normalized mode-4 pressure-only case.

So `dp=0.0065` is not simply "more resolved" for this operator. It gives a
better interior lattice but a rougher, more over-counted curved boundary
region.

## Boundary-Type Diagnosis

C5l supports this classification:

1. Mode `4` normalized is still an over-strong, nonuniform Robin-like boundary.
2. Mode `5` MLS improves some center/volume metrics but leaves surface shell
   pressure high.
3. Mode `6` is a radial FV boundary sink with inconsistent shell
   redistribution, not a validated true Dirichlet operator.

Mode `6`, `dp=0.010`, explains the key paradox. Its median flux ratio is close
to `1` (`1.078`) and final ratio is `0.784`, but its final surface shell mean
is still `577.06 Pa` versus the FV reference `85.9 Pa`. The global/boundary
flux can be roughly right while the radial pressure profile is wrong, because
the outer-shell sink, adjacent-shell exchange, and interior material-material
Laplacian do not form a consistent radial diffusion operator.

## Decision

C5l shows that the main blocker is near-boundary radial Laplacian /
shell-exchange consistency. Boundary flux strength alone is no longer the most
useful control variable.

Recommended next source route:

```text
C5m = conservative multi-shell radial exchange prototype
```

This is preferred over immediately returning to local MLS because the failing
mode-6 case already demonstrates that an integrated boundary sink can have a
reasonable global flux ratio while the shell profile remains wrong. The next
prototype should conserve shell storage and explicitly control exchange between
the outer shell and its adjacent interior shells.

C6 remains blocked. GPU remains deferred.
