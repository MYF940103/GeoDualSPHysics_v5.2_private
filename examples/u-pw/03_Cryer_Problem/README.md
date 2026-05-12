# 03 Cryer Problem

Reduced launch workflow and CPU smoke scaffold for the PR-formulation Cryer benchmark.

This directory now contains a runnable **Cryer-like strict/minimal smoke** case.
It is not a strict Cryer reproduction because the exact paper geometry/radius
and particle-consistent drained curved boundary treatment are still TODO.

It also contains an example-style **baseline launch workflow** for manual CPU/GPU
Release reruns. This workflow is intended to make Cryer setup exploration
reproducible before strict analytical reproduction is attempted.

## Files

- `CaseCryer_PR_Smoke_Def.xml`: reduced 2D column-style smoke using u-pw PR settings.
- `xCaseCryer_PR_Smoke_win64_CPU_debug.bat`: CPU Debug smoke runner.
- `CaseCryer_PR_Baseline_Def.xml`: reduced Cryer baseline launch XML using production `PorePressureBoundaryOperator=0`.
- `xCaseCryer_PR_Baseline_win64_CPU_release.bat`: example-style CPU Release workflow.
- `xCaseCryer_PR_Baseline_win64_GPU_release.bat`: example-style GPU Release workflow.
- `analyze_cryer_smoke.py`: near-center pore-pressure history helper.
- `cryer_smoke_center_pressure.csv`: latest smoke postprocessing summary.
- `CaseCryer_PR_TODO_Def.xml`: historical strict-reproduction placeholder.
- `smoke_status.md`: latest reduced smoke result.

## Current Status

- Cryer-like strict/minimal smoke is CPU runnable.
- Latest smoke: GenCase `code=0`, DualSPHysics `code=0`, `excluded=0`.
- Key pore-pressure fields are written.
- No NaN/Inf was detected in the generated `PartCsv_*.csv` files.
- The analysis helper reports a bounded near-center pore-pressure proxy.
- Baseline CPU/GPU Release BATs are prepared but were not run in C1-revised.
- Strict Cryer reproduction is still feature-blocked.

## Baseline Launch Workflow

The new baseline BATs follow the normal example pattern:

`GenCase -> DualSPHysics Release -> PartVTK`

CPU:

```bat
xCaseCryer_PR_Baseline_win64_CPU_release.bat
```

GPU:

```bat
xCaseCryer_PR_Baseline_win64_GPU_release.bat
```

The BATs generate complete raw output folders and complete fluid/material
particle VTK output for visualization. They do not run Python analysis, extract
selected frames, generate previews, or create metadata packages.

The baseline uses:

- `HydromechCoupling=1`
- `PorePressureModel=1`
- `SavePorePressure=1`
- `PorePressureBoundaryOperator=0`
- `PorePressureFeedback=1`
- `PorePressureFeedbackMode=1`
- `PorePressureFeedbackOperator=1`
- `PorePressureShepard=1`
- `PorePressureShepardInterval=10`
- `PorePressureShepardMode=1`
- `PorePressureDtSafety=0.20`

This remains a reduced workflow. It should not be cited as strict Cryer
analytical reproduction.

## Strict Reproduction Reclassification

This Cryer-like smoke must not be counted as strict Cryer reproduction complete.
It does not yet include the paper Cryer geometry, a drained spherical/curved
pore-pressure boundary, boundary ghost / MLS pressure reconstruction, or center
pore-pressure analytical postprocessing. Under the full CPU pre-GPU gate, Cryer
still blocks full strict reproduction until these gaps are implemented or
explicitly deferred.

## Missing Before Strict Cryer Reproduction

- Paper geometry/radius and exact benchmark parameters.
- 3D spherical or validated axisymmetric geometry.
- Drained pore-pressure boundary around the specimen.
- Pore-pressure ghost / MLS boundary treatment or another strict drained boundary strategy.
- Analytical center-pressure postprocessing.
- Likely GPU support for useful resolution.

## Minimum Future Strict Smoke Standard

A future strict smoke should be coarse and short:

- `code=0`;
- `excluded=0`;
- no NaN;
- pressure fields written;
- symmetric qualitative pressure response;
- center pore-pressure history available for later comparison.

## C2 Strict-Reference Audit

C2 added a documentation-only audit of the strict Cryer requirements. No
GenCase, CPU, GPU, or PartVTK run was performed.

The audit confirms that strict Cryer requires:

- a 3D sphere of radius `R=a` or a validated axisymmetric equivalent;
- all-around normal traction `p0`;
- a drained curved exterior pore-pressure boundary;
- center pressure output normalized as `p_w(r=0,t)/p0`;
- a verified Mandel-Cryer analytical reference and dimensionless time mapping;
- the Poisson-ratio sweep `0.1`, `0.2`, `0.3`, `0.45`.

The converted paper text contains the Cryer center-pressure analytical form and
root equation, but the extraction is not clean enough to use directly as a
trusted implementation. A clean PDF/manual formula check or digitized reference
curve is still needed before strict comparison.

## Next Step Options

- **C3-A reduced manual-run path:** keep the current baseline XML/BAT, prepare a
  center-pressure extraction script, and let users run the reduced workflow
  manually for qualitative response and visualization.
- **C3-B strict setup path:** recover the analytical reference, lock the sphere
  geometry and normalization, then decide whether CPU boundary/loading source
  work is needed before any GPU route.

Current recommendation: use C3-A for quick workflow progress, or C3-B if the
next milestone must be strict paper reproduction.

## C3-B Strict Route Preparation

C3-B starts the strict reproduction route. It does not run the baseline and it
does not claim validation. New planning files are under
`strict_reproduction_plan/`.

C3-B decisions:

- strict geometry should start from a true 3D sphere, not the reduced column;
- the analytical center-pressure formula has been transcribed from the local
  PDF, but still needs a C4 reference script and Figure 7B check;
- all-around traction `p0` must not be faked as gravity or top compression;
- drained curved pore-pressure boundary remains a strict blocker;
- GPU should wait until CPU reference, geometry, loading, and boundary are
  credible.

Draft files:

- `strict_reproduction_plan/CaseCryer_PR_StrictSphere_Draft_Def.xml`
- `strict_reproduction_plan/strict_reference_notes.md`
- `strict_reproduction_plan/strict_geometry_notes.md`
- `strict_reproduction_plan/strict_loading_boundary_notes.md`

The draft XML is intentionally marked as not validated and not ready to run.
It does not replace `CaseCryer_PR_Baseline_Def.xml`.

## C4-A Analytical Reference Script

C4-A implemented the standalone analytical reference generator:

```powershell
py strict_reproduction_plan\cryer_reference_solution.py --make-plot
```

Outputs are written to `strict_reproduction_plan/`:

- `cryer_reference_curves.csv`
- `cryer_reference_roots.csv`
- `cryer_reference_convergence.csv`
- `cryer_reference_peak_metrics.csv`
- `cryer_reference_selfcheck.json`
- `figures/cryer_reference_center_pressure_curves.*`
- `figures/cryer_reference_root_convergence.*`
- `figures/cryer_reference_peak_vs_nu.*`
- `figures/cryer_reference_long_time_decay.*`

The script generates curves for `nu=0.1`, `0.2`, `0.3`, and `0.45`, and it
shows the expected Mandel-Cryer peak ordering. No Figure 7B digitized data is
currently available, so the curves are analytical reference candidates rather
than a completed paper-figure validation.

Strict simulation is still not started. The next strict task is C4-B:
all-around spherical traction support audit.
