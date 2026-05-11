# GPU G9/G9b Self-Weight Scenario 2 Analytical Comparison

Date: 2026-05-11

## Objective

This report compares the two existing GPU self-weight Scenario 2 long-run
results against analytical curves reconstructed from the local Supporting
Information notes:

- G9: `HydromechDampingXi=0.10`;
- G9b: `HydromechDampingXi=0.05`.

No source code was modified and no new long run was executed.

## Data Sources

Simulation results:

```text
examples/u-pw/02_SelfWeight_Consolidation/experiments/GPU_G9_SelfWeightLong/
examples/u-pw/02_SelfWeight_Consolidation/experiments/GPU_G9b_SelfWeightLong_Xi005/
```

Reference material:

- `src/papers/u-p/supporting_information_implementation_notes.md`, Section 3.
- `src/papers/u-p/converted/u_pw_paper_text.md`, Section 4.1 for the 1D
  consolidation coefficient and Terzaghi-style series context.

No machine-readable discrete Supporting Information figure data were found in
the repository. The analytical curves were therefore reconstructed from the
available formulas.

## Analytical Reconstruction

The Supporting Information notes give the initial undrained self-weight pore
pressure response:

```text
p0(z) = [(Kw/n) rho g (H-z)] / [K + 4G/3 + Kw/n]
```

with:

```text
K = E / [3(1-2nu)]
G = E / [2(1+nu)]
```

The dissipation basis uses the cosine series documented in the same notes:

```text
u(z,t) = sum_n A_n cos(lambda_n z) exp(-lambda_n^2 cv t)
lambda_n = (2n+1) pi / (2H)
```

For Scenario 2, body gravity remains active and the final state is hydrostatic.
The comparison therefore reconstructs:

```text
p_total(z,t) = p_hydro(z) + u(z,t)
```

where `u` is the decaying excess pressure. The drainage clock starts at
`PorePressureTopDrainedStartTime=0.002 s`; the saved `Part_0000` frame is the
pre-undrained hydrostatic initialization and is omitted from error metrics.

Parameters used:

| Parameter | Value |
|---|---:|
| `E` | `2.0e6 Pa` |
| `nu` | `0.3` |
| `K` | `1.6666667e6 Pa` |
| `G` | `7.6923077e5 Pa` |
| `M=K+4G/3` | `2.6923077e6 Pa` |
| `Kw` | `2.0e8 Pa` |
| `n` | `0.3` |
| `k` | `1.0e-3 m/s` |
| `rho_w` | `1000 kg/m3` |
| `rho` | `2100 kg/m3` |
| `H` | `0.99 m` from retained frame metrics |
| `cv=k*M/(rho_w*g)` | `0.274445 m2/s` |

The reconstructed analytical initial bottom excess is `20299.23 Pa`.

Important limitation: raw particle `PartCsv_*.csv` files were intentionally
cleaned after G9/G9b. Time-series comparisons use retained metrics CSV files.
Profile comparisons use approximate profile values recovered from retained SVG
profile figures; these profile metrics are therefore approximate and are marked
as such in the CSV.

## Generated Files

Analysis output directory:

```text
examples/u-pw/02_SelfWeight_Consolidation/experiments/GPU_G9b_SelfWeightLong_Xi005/analytical_comparison/
```

Files:

- `analytical_solution_notes.md`
- `analytical_comparison_metrics.csv`
- `analytical_profile_timeseries.csv`
- `analytical_bottom_timeseries.csv`
- `compare_g9_g9b_analytical.py`

Figures, SVG and PNG:

- `gpu_g9_g9b_vs_analytical_porepress_profiles`
- `gpu_g9_g9b_vs_analytical_excess_profiles`
- `gpu_g9_g9b_vs_analytical_bottom_porepress_time`
- `gpu_g9_g9b_vs_analytical_bottom_excess_time`
- `gpu_g9_g9b_vs_analytical_excess_envelope`
- `gpu_g9_g9b_vs_analytical_normalized_comparison`

## Error Metrics

Time-series metrics use retained frame metrics and omit `t=0`.

| Quantity | xi=0.10 RMSE | xi=0.05 RMSE | Closer |
|---|---:|---:|---|
| bottom excess pressure | `585.50 Pa` | `550.17 Pa` | xi=0.05 |
| bottom total pore pressure | `584.58 Pa` | `549.17 Pa` | xi=0.05 |
| excess envelope | `584.68 Pa` | `549.39 Pa` | xi=0.05 |

Corresponding max absolute errors:

| Quantity | xi=0.10 max abs | xi=0.05 max abs | Closer |
|---|---:|---:|---|
| bottom excess pressure | `922.99 Pa` | `714.78 Pa` | xi=0.05 |
| bottom total pore pressure | `922.68 Pa` | `713.84 Pa` | xi=0.05 |
| excess envelope | `920.25 Pa` | `713.88 Pa` | xi=0.05 |

Approximate profile metrics recovered from SVG:

| Quantity | xi=0.10 mean RMSE over target profiles | xi=0.05 mean RMSE over target profiles | Closer |
|---|---:|---:|---|
| excess profiles | `281.92 Pa` | `214.56 Pa` | xi=0.05 |
| total pore-pressure profiles | `208.46 Pa` | `167.55 Pa` | xi=0.05 |

The target profile times are `0.1`, `0.5`, `1.0`, `2.0`, and `3.6 s`.
The `t=0` saved GPU frame is not directly comparable because it is the
pre-undrained hydrostatic initialization.

## xi=0.10 vs Analytical

The `xi=0.10` line is stable and follows the reconstructed analytical trend,
but it is lower than the analytical bottom-excess curve throughout the retained
post-drainage frames. At `3.6 s`, final bottom excess is about `1160 Pa` versus
analytical `1371 Pa`. The integrated time-series RMSE is larger than the
`xi=0.05` line because of larger early and mid-time deviations.

This line remains a good stability-diagnostic choice.

## xi=0.05 vs Analytical

The `xi=0.05` line is the more paper-compatible damping setting and is also
closer to the reconstructed analytical line in the retained metrics:

- bottom excess RMSE improves by about `35 Pa`;
- bottom total pressure RMSE improves by about `35 Pa`;
- max absolute bottom error improves by about `208 Pa`;
- approximate profile RMSE also improves overall.

It ran slower than `xi=0.10`, but it remained stable to `3.6 s` with
`code=0` and `excluded=0`.

## Which Damping Line Is Closer?

Based on the analytical reconstruction and retained metrics, `xi=0.05` is
closer to the analytical Scenario 2 trend than `xi=0.10`.

The difference is not a new physics change; it primarily changes the damping of
the coupled mechanical response. The `xi=0.05` line is therefore the preferred
paper-compatible line, while `xi=0.10` remains useful for stability diagnostics.

## Recommendation

Keep both lines:

- use `xi=0.05` as the paper-compatible Scenario 2 comparison;
- use `xi=0.10` as the conservative stability-diagnostic line.

The next u-pw task can move to GPU Scenario 1 staged workflow design. That
should first decide whether Scenario 1 on GPU uses a restart path that restores
`PorePressg`, or a single-run gravity-stop route. No new long-run Scenario 2
calculation is needed before that decision.
