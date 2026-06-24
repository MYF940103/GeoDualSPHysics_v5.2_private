# Cryer Poisson-ratio sweep results

Date: 2026-06-23

## Source results

The combined plot uses the completed server outputs in the case root:

- `CaseCryerProblem_PR_nu010_out`
- `CaseCryerProblem_PR_nu020_out`
- `CaseCryerProblem_PR_out`
- `CaseCryerProblem_PR_nu045_out`

Each group contains `1001` particle VTK files. The center pore pressure was
sampled with `r <= 1dp`.

## Generated files

- `support/plot_cryer_poisson_sweep.py`
- `figures/cryer_poisson_nu010_center_r1dp.csv`
- `figures/cryer_poisson_nu020_center_r1dp.csv`
- `figures/cryer_poisson_nu030_center_r1dp.csv`
- `figures/cryer_poisson_nu045_center_r1dp.csv`
- `figures/cryer_poisson_sweep_center_r1dp.csv`
- `figures/cryer_poisson_sweep_center_r1dp_metrics.json`
- `figures/cryer_poisson_sweep_center_r1dp_paper_axes.png`
- `figures/cryer_poisson_sweep_center_r1dp_paper_axes.pdf`

The plotting convention follows the u-pw paper's Figure 7B comparison:
normalized center pore pressure `p^w(0,t)/p0` versus dimensionless time `T_v`
for `nu = 0.1, 0.2, 0.3, 0.45`.

## Metrics

| nu | SPH peak | SPH peak Tv | Analytical peak | Analytical peak Tv | RMSE |
|---:|---:|---:|---:|---:|---:|
| 0.1 | 1.424451 | 0.064 | 1.472748 | 0.058 | 0.036567 |
| 0.2 | 1.322840 | 0.057 | 1.364264 | 0.052 | 0.029579 |
| 0.3 | 1.215952 | 0.049 | 1.249007 | 0.046 | 0.022761 |
| 0.45 | 1.222957 | 0.003 | 1.062771 | 0.034 | 0.017642 |

## Interpretation

The `nu = 0.1, 0.2, 0.3` groups reproduce the expected trend: lower Poisson
ratio gives a higher Mandel-Cryer pore-pressure peak, and the SPH peak timing
is slightly delayed relative to the analytical curve.

For `nu = 0.45`, the analytical peak is small and early startup oscillation
becomes the global numerical maximum. The value at the analytical peak time is
`p/p0 = 1.040668`, compared with the analytical `1.062771`; therefore the main
curve shape is still close after the startup transient, but the raw global
maximum should not be interpreted as the physical Cryer peak for this group.
