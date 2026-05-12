# Strict Cryer Reproduction Plan

This directory contains draft planning files for the strict Cryer track. These
files are not validation results and should not be run as production examples
until the TODOs are resolved.

Strict target:

- 3D poroelastic sphere with radius `R=a`;
- all-around normal traction `p0`;
- drained curved exterior pore-pressure boundary;
- center pressure `p_w(0,t)/p0`;
- dimensionless time `T_v = c_v t / a^2`;
- Poisson sweep `nu=0.1`, `0.2`, `0.3`, `0.45`.

Current files:

- `CaseCryer_PR_StrictSphere_Draft_Def.xml`: non-validated XML skeleton for a
  future true-sphere setup. It explicitly sets `SoilConstitutiveModel=0`
  because strict Cryer is linear poroelastic.
- `strict_geometry_notes.md`: geometry choices and TODOs.
- `strict_reference_notes.md`: analytical reference formula and validation
  checklist.
- `strict_loading_boundary_notes.md`: loading and drained-boundary blockers.

The existing `../CaseCryer_PR_Baseline_Def.xml` remains the reduced launch
workflow. It is not replaced by this strict plan.

## Analytical Reference Script

Run from this directory:

```powershell
py cryer_reference_solution.py --make-plot
```

The script writes:

- `cryer_reference_curves.csv`
- `cryer_reference_roots.csv`
- `cryer_reference_convergence.csv`
- `cryer_reference_peak_metrics.csv`
- `cryer_reference_selfcheck.json`
- `figures/cryer_reference_center_pressure_curves.*`
- `figures/cryer_reference_root_convergence.*`
- `figures/cryer_reference_peak_vs_nu.*`
- `figures/cryer_reference_long_time_decay.*`

Digitized Figure 7B data is optional and not currently available. See
`fig7b_digitization_README.md`.
